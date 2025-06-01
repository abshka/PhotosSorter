#!/usr/bin/env python3
"""
Async File Organizer Module

This module provides an asynchronous file organizer for improved performance
when processing large numbers of files. It uses async I/O operations and
concurrent processing to maximize throughput while maintaining thread safety.
"""

import asyncio
import logging
import aiofiles
import aiofiles.os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, AsyncGenerator, Any
import concurrent.futures
from dataclasses import dataclass
import time

try:
    from .exif_extractor import ExifExtractor
    from .utils.statistics import StatisticsCollector
    from .utils.exceptions import PhotoSorterError, PhotoSorterFileNotFoundError
    from .utils.interfaces import LoggerMixin, ConfigurableMixin
except ImportError:
    from exif_extractor import ExifExtractor
    from utils.statistics import StatisticsCollector
    from utils.exceptions import PhotoSorterError, PhotoSorterFileNotFoundError
    from utils.interfaces import LoggerMixin, ConfigurableMixin


@dataclass
class FileTask:
    """Represents a file processing task."""
    source_path: Path
    target_path: Path
    operation: str  # 'move', 'copy', 'merge'
    priority: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessingResult:
    """Represents the result of a file processing operation."""
    task: FileTask
    success: bool
    error: Optional[str] = None
    duration: float = 0.0
    bytes_processed: int = 0


class AsyncFileOrganizer(ConfigurableMixin, LoggerMixin):
    """
    Asynchronous file organizer for high-performance photo processing.
    
    Features:
    - Async I/O operations for better throughput
    - Concurrent processing with configurable worker pools
    - Progress tracking and cancellation support
    - Memory-efficient streaming for large files
    - Automatic retry mechanisms for transient failures
    """
    
    def __init__(self, config: Dict, max_workers: int = 4, max_concurrent_io: int = 10):
        """
        Initialize the async file organizer.
        
        Args:
            config (Dict): Configuration dictionary
            max_workers (int): Maximum number of worker threads for CPU-bound tasks
            max_concurrent_io (int): Maximum concurrent I/O operations
        """
        super().__init__(config=config)
        
        self.max_workers = max_workers
        self.max_concurrent_io = max_concurrent_io
        
        # Async components
        self._io_semaphore = asyncio.Semaphore(max_concurrent_io)
        self._task_queue = asyncio.Queue()
        self._result_queue = asyncio.Queue()
        self._workers = []
        self._is_processing = False
        self._cancel_event = asyncio.Event()
        
        # Thread pool for CPU-bound operations
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Components
        self.exif_extractor = ExifExtractor()
        self.stats_collector = StatisticsCollector()
        
        # Performance tracking
        self._processed_files = 0
        self._total_bytes = 0
        self._start_time = None
        
        # Configuration shortcuts
        self.dry_run = self.get_config_value('safety.dry_run', False)
        self.move_files = self.get_config_value('processing.move_files', False)
        self.batch_size = self.get_config_value('performance.batch_size', 100)
        self.retry_attempts = self.get_config_value('performance.retry_attempts', 3)
        
    async def organize_photos_async(self, source_dir: str, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Main asynchronous method to organize photos.
        
        Args:
            source_dir (str): Source directory containing photos
            target_dir (Optional[str]): Target directory for organized photos
            
        Returns:
            Dict[str, Any]: Processing statistics and results
        """
        self.logger.info(f"Starting async photo organization: {source_dir}")
        self._start_time = time.time()
        self.stats_collector.start_session()
        
        try:
            # Validate paths
            source_path, target_path = await self._validate_paths(source_dir, target_dir)
            
            # Discover files
            self.logger.info("Discovering media files...")
            file_paths = await self._discover_files_async(source_path)
            total_files = len(file_paths)
            
            if total_files == 0:
                self.logger.warning("No supported files found")
                return self._get_final_stats()
            
            self.logger.info(f"Found {total_files} files to process")
            
            # Start processing workers
            await self._start_workers()
            
            # Generate processing tasks
            task_generator = self._generate_tasks_async(file_paths, target_path)
            
            # Process files in batches
            batch_count = 0
            async for batch in self._batch_generator(task_generator, self.batch_size):
                if self._cancel_event.is_set():
                    break
                    
                batch_count += 1
                self.logger.debug(f"Processing batch {batch_count}")
                
                # Queue tasks for processing
                for task in batch:
                    await self._task_queue.put(task)
                
                # Wait for batch completion with timeout
                await self._wait_for_batch_completion(len(batch))
            
            # Signal completion and wait for workers to finish
            await self._stop_workers()
            
            # Final statistics
            return self._get_final_stats()
            
        except Exception as e:
            self.logger.error(f"Error during async organization: {e}")
            await self._cleanup()
            raise PhotoSorterError(f"Async organization failed: {e}")
        
        finally:
            self.stats_collector.end_session()
    
    async def _validate_paths(self, source_dir: str, target_dir: Optional[str]) -> Tuple[Path, Path]:
        """
        Validate and prepare source and target paths asynchronously.
        
        Args:
            source_dir (str): Source directory path
            target_dir (Optional[str]): Target directory path
            
        Returns:
            Tuple[Path, Path]: Validated source and target paths
        """
        source_path = Path(source_dir)
        
        if not await aiofiles.os.path.exists(source_path):
            raise PhotoSorterFileNotFoundError(f"Source directory does not exist: {source_path}")
        
        if not await aiofiles.os.path.isdir(source_path):
            raise PhotoSorterError(f"Source path is not a directory: {source_path}")
        
        # Determine target path
        if target_dir:
            target_path = Path(target_dir)
            # Create target directory if it doesn't exist
            await aiofiles.os.makedirs(target_path, exist_ok=True)
        else:
            target_path = source_path
        
        return source_path, target_path
    
    async def _discover_files_async(self, directory: Path) -> List[Path]:
        """
        Asynchronously discover supported media files in directory.
        
        Args:
            directory (Path): Directory to scan
            
        Returns:
            List[Path]: List of discovered file paths
        """
        supported_extensions = set(
            ext.lower() for ext in self.get_config_value('supported_extensions', [])
        )
        
        files = []
        
        async def scan_directory(dir_path: Path):
            """Recursively scan directory for supported files."""
            try:
                async for entry in aiofiles.os.scandir(dir_path):
                    if await aiofiles.os.path.isfile(entry.path):
                        file_path = Path(entry.path)
                        if file_path.suffix.lower() in supported_extensions:
                            files.append(file_path)
                    elif await aiofiles.os.path.isdir(entry.path):
                        # Skip organized directories to avoid re-processing
                        if not self._is_organized_directory(Path(entry.path)):
                            await scan_directory(Path(entry.path))
            except Exception as e:
                self.logger.warning(f"Error scanning directory {dir_path}: {e}")
        
        await scan_directory(directory)
        
        # Sort files for consistent processing order
        files.sort()
        return files
    
    def _is_organized_directory(self, directory: Path) -> bool:
        """
        Check if directory appears to be organized (follows date format).
        
        Args:
            directory (Path): Directory to check
            
        Returns:
            bool: True if directory appears organized
        """
        dir_name = directory.name
        
        # Check if directory name matches date formats
        date_patterns = [
            r'^\d{4}$',           # Year: 2024
            r'^\d{4}-\d{2}$',     # Year-Month: 2024-01
            r'^\d{4}-\d{2}-\d{2}$',  # Year-Month-Day: 2024-01-15
            r'^\d{2}$',           # Month: 01
            r'^\d{2}-\d{2}$',     # Month-Day: 01-15
        ]
        
        import re
        for pattern in date_patterns:
            if re.match(pattern, dir_name):
                return True
        
        return False
    
    async def _generate_tasks_async(self, file_paths: List[Path], target_base: Path) -> AsyncGenerator[FileTask, None]:
        """
        Asynchronously generate processing tasks for files.
        
        Args:
            file_paths (List[Path]): List of file paths to process
            target_base (Path): Base target directory
            
        Yields:
            FileTask: File processing task
        """
        for file_path in file_paths:
            if self._cancel_event.is_set():
                break
            
            try:
                # Extract date asynchronously
                creation_date = await self._extract_date_async(file_path)
                
                # Determine target path based on date
                if creation_date:
                    target_dir = self._get_target_directory_for_date(creation_date, target_base)
                else:
                    target_dir = target_base / self.get_config_value('fallback.no_date_folder', 'Unknown_Date')
                
                target_path = target_dir / file_path.name
                
                # Handle duplicates
                target_path = await self._handle_duplicate_async(target_path)
                
                # Create task
                operation = 'move' if self.move_files else 'copy'
                task = FileTask(
                    source_path=file_path,
                    target_path=target_path,
                    operation=operation,
                    metadata={'creation_date': creation_date}
                )
                
                yield task
                
            except Exception as e:
                self.logger.error(f"Error generating task for {file_path}: {e}")
                self.stats_collector.increment('errors')
    
    async def _extract_date_async(self, file_path: Path) -> Optional[datetime]:
        """
        Extract creation date from file asynchronously.
        
        Args:
            file_path (Path): File to extract date from
            
        Returns:
            Optional[datetime]: Extracted date or None
        """
        # Run EXIF extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            date = await loop.run_in_executor(
                self._thread_pool,
                self.exif_extractor.extract_date_from_file,
                str(file_path)
            )
            return date
        except Exception as e:
            self.logger.debug(f"Error extracting date from {file_path}: {e}")
            return None
    
    def _get_target_directory_for_date(self, date: datetime, base_dir: Path) -> Path:
        """
        Get target directory path for a given date.
        
        Args:
            date (datetime): File creation date
            base_dir (Path): Base directory
            
        Returns:
            Path: Target directory path
        """
        date_format = self.get_config_value('date_format', 'YYYY/MM/DD')
        
        if date_format == 'YYYY/MM/DD':
            return base_dir / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"
        elif date_format == 'YYYY/MM':
            return base_dir / f"{date.year:04d}" / f"{date.month:02d}"
        elif date_format == 'YYYY-MM-DD':
            return base_dir / f"{date.year:04d}-{date.month:02d}-{date.day:02d}"
        elif date_format == 'YYYY-MM':
            return base_dir / f"{date.year:04d}-{date.month:02d}"
        else:
            # Default fallback
            return base_dir / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"
    
    async def _handle_duplicate_async(self, target_path: Path) -> Path:
        """
        Handle duplicate filenames asynchronously.
        
        Args:
            target_path (Path): Original target path
            
        Returns:
            Path: Final target path (possibly renamed)
        """
        if not await aiofiles.os.path.exists(target_path):
            return target_path
        
        duplicate_handling = self.get_config_value('processing.duplicate_handling', 'rename')
        
        if duplicate_handling == 'skip':
            return target_path
        elif duplicate_handling == 'overwrite':
            return target_path
        elif duplicate_handling == 'rename':
            # Find available filename
            base = target_path.stem
            suffix = target_path.suffix
            parent = target_path.parent
            counter = 1
            
            while True:
                new_name = f"{base}_{counter:03d}{suffix}"
                new_path = parent / new_name
                if not await aiofiles.os.path.exists(new_path):
                    return new_path
                counter += 1
                
                # Prevent infinite loops
                if counter > 9999:
                    self.logger.warning(f"Too many duplicates for {target_path}")
                    return target_path
        
        return target_path
    
    async def _start_workers(self):
        """Start async worker tasks."""
        self._is_processing = True
        self._cancel_event.clear()
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        self.logger.debug(f"Started {len(self._workers)} worker tasks")
    
    async def _stop_workers(self):
        """Stop async worker tasks."""
        self._is_processing = False
        
        # Send stop signals
        for _ in self._workers:
            await self._task_queue.put(None)
        
        # Wait for workers to complete
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        self.logger.debug("All workers stopped")
    
    async def _worker(self, worker_id: str):
        """
        Async worker for processing file tasks.
        
        Args:
            worker_id (str): Unique worker identifier
        """
        self.logger.debug(f"Worker {worker_id} started")
        
        while self._is_processing or not self._task_queue.empty():
            try:
                # Get next task with timeout
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                
                if task is None:  # Stop signal
                    break
                
                # Process task
                result = await self._process_task_async(task, worker_id)
                await self._result_queue.put(result)
                
                # Mark task as done
                self._task_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
        
        self.logger.debug(f"Worker {worker_id} stopped")
    
    async def _process_task_async(self, task: FileTask, worker_id: str) -> ProcessingResult:
        """
        Process a single file task asynchronously.
        
        Args:
            task (FileTask): Task to process
            worker_id (str): Processing worker ID
            
        Returns:
            ProcessingResult: Result of processing
        """
        start_time = time.time()
        
        try:
            if self.dry_run:
                # Simulate processing for dry run
                await asyncio.sleep(0.001)
                self.logger.debug(f"[DRY RUN] {task.operation}: {task.source_path} -> {task.target_path}")
                success = True
                error = None
                bytes_processed = 0
            else:
                # Actual file processing
                success, error, bytes_processed = await self._execute_file_operation(task)
            
            duration = time.time() - start_time
            
            # Update statistics
            if success:
                self.stats_collector.increment('processed')
                if task.operation == 'move':
                    self.stats_collector.increment('moved')
                elif task.operation == 'copy':
                    self.stats_collector.increment('copied')
                
                self._processed_files += 1
                self._total_bytes += bytes_processed
            else:
                self.stats_collector.increment('errors')
            
            return ProcessingResult(
                task=task,
                success=success,
                error=error,
                duration=duration,
                bytes_processed=bytes_processed
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {e}"
            self.logger.error(f"Task processing failed: {error_msg}")
            self.stats_collector.increment('errors')
            
            return ProcessingResult(
                task=task,
                success=False,
                error=error_msg,
                duration=duration,
                bytes_processed=0
            )
    
    async def _execute_file_operation(self, task: FileTask) -> Tuple[bool, Optional[str], int]:
        """
        Execute the actual file operation with retry logic.
        
        Args:
            task (FileTask): Task to execute
            
        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, bytes_processed)
        """
        for attempt in range(self.retry_attempts):
            try:
                async with self._io_semaphore:  # Limit concurrent I/O
                    # Ensure target directory exists
                    await aiofiles.os.makedirs(task.target_path.parent, exist_ok=True)
                    
                    # Get file size
                    file_stat = await aiofiles.os.stat(task.source_path)
                    file_size = file_stat.st_size
                    
                    if task.operation == 'move':
                        await self._move_file_async(task.source_path, task.target_path)
                    elif task.operation == 'copy':
                        await self._copy_file_async(task.source_path, task.target_path)
                    
                    return True, None, file_size
                    
            except Exception as e:
                error_msg = f"Attempt {attempt + 1}/{self.retry_attempts} failed: {e}"
                self.logger.warning(error_msg)
                
                if attempt == self.retry_attempts - 1:
                    return False, str(e), 0
                
                # Wait before retry with exponential backoff
                await asyncio.sleep(0.1 * (2 ** attempt))
        
        return False, "Max retries exceeded", 0
    
    async def _move_file_async(self, source: Path, target: Path):
        """
        Move file asynchronously.
        
        Args:
            source (Path): Source file path
            target (Path): Target file path
        """
        await aiofiles.os.rename(source, target)
    
    async def _copy_file_async(self, source: Path, target: Path):
        """
        Copy file asynchronously with streaming for large files.
        
        Args:
            source (Path): Source file path
            target (Path): Target file path
        """
        chunk_size = 64 * 1024  # 64KB chunks
        
        async with aiofiles.open(source, 'rb') as src:
            async with aiofiles.open(target, 'wb') as dst:
                while True:
                    chunk = await src.read(chunk_size)
                    if not chunk:
                        break
                    await dst.write(chunk)
        
        # Preserve file metadata
        await self._copy_metadata_async(source, target)
    
    async def _copy_metadata_async(self, source: Path, target: Path):
        """
        Copy file metadata asynchronously.
        
        Args:
            source (Path): Source file path
            target (Path): Target file path
        """
        try:
            source_stat = await aiofiles.os.stat(source)
            await aiofiles.os.utime(target, (source_stat.st_atime, source_stat.st_mtime))
        except Exception as e:
            self.logger.debug(f"Could not copy metadata from {source} to {target}: {e}")
    
    async def _batch_generator(self, async_generator, batch_size: int):
        """
        Generate batches from an async generator.
        
        Args:
            async_generator: Async generator to batch
            batch_size (int): Size of each batch
            
        Yields:
            List: Batch of items
        """
        batch = []
        async for item in async_generator:
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:  # Yield remaining items
            yield batch
    
    async def _wait_for_batch_completion(self, batch_size: int, timeout: float = 30.0):
        """
        Wait for a batch of tasks to complete.
        
        Args:
            batch_size (int): Number of tasks in batch
            timeout (float): Maximum time to wait
        """
        completed = 0
        start_time = time.time()
        
        while completed < batch_size and (time.time() - start_time) < timeout:
            try:
                await asyncio.wait_for(self._result_queue.get(), timeout=1.0)
                completed += 1
                self._result_queue.task_done()
            except asyncio.TimeoutError:
                if self._cancel_event.is_set():
                    break
                continue
        
        if completed < batch_size:
            self.logger.warning(f"Batch completion timeout: {completed}/{batch_size} tasks completed")
    
    def _get_final_stats(self) -> Dict[str, Any]:
        """
        Get final processing statistics.
        
        Returns:
            Dict[str, Any]: Final statistics
        """
        elapsed_time = time.time() - self._start_time if self._start_time else 0
        
        stats = self.stats_collector.get_dict()
        stats.update({
            'total_files': self._processed_files,
            'total_bytes': self._total_bytes,
            'elapsed_time': elapsed_time,
            'files_per_second': self._processed_files / elapsed_time if elapsed_time > 0 else 0,
            'bytes_per_second': self._total_bytes / elapsed_time if elapsed_time > 0 else 0,
            'async_processing': True
        })
        
        return stats
    
    async def cancel_processing(self):
        """Cancel ongoing processing."""
        self.logger.info("Cancelling async processing...")
        self._cancel_event.set()
        await self._cleanup()
    
    async def _cleanup(self):
        """Clean up resources."""
        if self._workers:
            await self._stop_workers()
        
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)
    
    async def get_processing_status(self) -> Dict[str, Any]:
        """
        Get current processing status.
        
        Returns:
            Dict[str, Any]: Processing status information
        """
        elapsed_time = time.time() - self._start_time if self._start_time else 0
        
        return {
            'is_processing': self._is_processing,
            'files_processed': self._processed_files,
            'bytes_processed': self._total_bytes,
            'elapsed_time': elapsed_time,
            'workers_active': len(self._workers),
            'queue_size': self._task_queue.qsize(),
            'files_per_second': self._processed_files / elapsed_time if elapsed_time > 0 else 0
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, '_thread_pool') and self._thread_pool:
            self._thread_pool.shutdown(wait=False)


async def main():
    """Test function for the async file organizer."""
    import tempfile
    import yaml
    
    # Create test configuration
    config = {
        'source_directory': tempfile.gettempdir(),
        'supported_extensions': ['.jpg', '.jpeg', '.png'],
        'processing': {'move_files': False},
        'safety': {'dry_run': True},
        'performance': {'batch_size': 10}
    }
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    organizer = AsyncFileOrganizer(config, max_workers=2, max_concurrent_io=5)
    
    try:
        stats = await organizer.organize_photos_async(config['source_directory'])
        print("Processing completed!")
        print(f"Statistics: {stats}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await organizer._cleanup()


if __name__ == "__main__":
    asyncio.run(main())