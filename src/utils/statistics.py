#!/usr/bin/env python3
"""
Statistics Collector Module

This module provides centralized statistics collection and reporting
for the PhotosSorter application.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessingStats:
    """Data class for processing statistics."""
    processed: int = 0
    moved: int = 0
    copied: int = 0
    skipped: int = 0
    errors: int = 0
    no_date: int = 0
    videos_processed: int = 0
    thumbnails_processed: int = 0
    mpg_merged: int = 0
    thm_deleted: int = 0
    mpg_deleted: int = 0
    backups_created: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    prev_thm_deleted: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()


class StatisticsCollector:
    """
    Centralized statistics collector for PhotosSorter operations.
    """
    
    def __init__(self):
        """Initialize the statistics collector."""
        self.logger = logging.getLogger(__name__)
        self.stats = ProcessingStats()
        self._operation_log = []
    
    def reset(self):
        """Reset all statistics."""
        self.stats = ProcessingStats()
        self._operation_log = []
        self.logger.debug("Statistics reset")
    
    def start_session(self):
        """Start a new processing session."""
        self.stats.start_time = datetime.now()
        self.logger.debug("Processing session started")
    
    def end_session(self):
        """End the current processing session."""
        self.stats.end_time = datetime.now()
        self.logger.debug("Processing session ended")
    
    def increment(self, counter: str, amount: int = 1):
        """
        Increment a counter.
        
        Args:
            counter (str): Name of the counter to increment
            amount (int): Amount to increment by (default: 1)
        """
        if hasattr(self.stats, counter):
            current_value = getattr(self.stats, counter)
            setattr(self.stats, counter, current_value + amount)
            self.logger.debug(f"Incremented {counter} by {amount} (now: {current_value + amount})")
        else:
            self.logger.warning(f"Unknown counter: {counter}")
    
    def set_counter(self, counter: str, value: int):
        """
        Set a counter to a specific value.
        
        Args:
            counter (str): Name of the counter to set
            value (int): Value to set
        """
        if hasattr(self.stats, counter):
            setattr(self.stats, counter, value)
            self.logger.debug(f"Set {counter} to {value}")
        else:
            self.logger.warning(f"Unknown counter: {counter}")
    
    def log_operation(self, operation_type: str, source: Path, target: Path, success: bool, error: Optional[str] = None):
        """
        Log an individual operation.
        
        Args:
            operation_type (str): Type of operation (move, copy, merge, etc.)
            source (Path): Source file path
            target (Path): Target file path
            success (bool): Whether the operation was successful
            error (str): Error message if operation failed
        """
        operation = {
            'timestamp': datetime.now(),
            'type': operation_type,
            'source': str(source),
            'target': str(target),
            'success': success,
            'error': error
        }
        self._operation_log.append(operation)
        
        if success:
            self.increment('processed')
            if operation_type == 'move':
                self.increment('moved')
            elif operation_type == 'copy':
                self.increment('copied')
            elif operation_type == 'merge':
                self.increment('mpg_merged')
        else:
            self.increment('errors')
    
    def get_duration(self) -> Optional[float]:
        """
        Get the duration of the processing session in seconds.
        
        Returns:
            Optional[float]: Duration in seconds, None if session not complete
        """
        if self.stats.start_time and self.stats.end_time:
            return (self.stats.end_time - self.stats.start_time).total_seconds()
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of statistics.
        
        Returns:
            Dict[str, Any]: Statistics summary
        """
        duration = self.get_duration()
        
        summary = {
            'counters': {
                'processed': self.stats.processed,
                'moved': self.stats.moved,
                'copied': self.stats.copied,
                'skipped': self.stats.skipped,
                'errors': self.stats.errors,
                'no_date': self.stats.no_date,
                'videos_processed': self.stats.videos_processed,
                'thumbnails_processed': self.stats.thumbnails_processed,
                'mpg_merged': self.stats.mpg_merged,
                'thm_deleted': self.stats.thm_deleted,
                'mpg_deleted': self.stats.mpg_deleted,
                'backups_created': self.stats.backups_created,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses
            },
            'timing': {
                'start_time': self.stats.start_time.isoformat() if self.stats.start_time else None,
                'end_time': self.stats.end_time.isoformat() if self.stats.end_time else None,
                'duration_seconds': duration
            },
            'performance': {
                'files_per_second': self.stats.processed / duration if duration and duration > 0 else 0,
                'cache_hit_rate': (
                    self.stats.cache_hits / (self.stats.cache_hits + self.stats.cache_misses)
                    if (self.stats.cache_hits + self.stats.cache_misses) > 0 else 0
                )
            },
            'operation_log_count': len(self._operation_log)
        }
        
        return summary
    
    def get_dict(self) -> Dict[str, int]:
        """
        Get statistics as a dictionary (for backward compatibility).
        
        Returns:
            Dict[str, int]: Statistics dictionary
        """
        return {
            'processed': self.stats.processed,
            'moved': self.stats.moved,
            'copied': self.stats.copied,
            'skipped': self.stats.skipped,
            'errors': self.stats.errors,
            'no_date': self.stats.no_date,
            'videos_processed': self.stats.videos_processed,
            'thumbnails_processed': self.stats.thumbnails_processed,
            'mpg_merged': self.stats.mpg_merged,
            'thm_deleted': self.stats.thm_deleted,
            'mpg_deleted': self.stats.mpg_deleted,
            'backups_created': self.stats.backups_created,
            'cache_hits': self.stats.cache_hits,
            'cache_misses': self.stats.cache_misses,
            'prev_thm_deleted': self.stats.prev_thm_deleted
        }
    
    def print_summary(self):
        """Print a formatted summary of statistics."""
        summary = self.get_summary()
        duration = summary['timing']['duration_seconds']
        
        print("=" * 60)
        print("PHOTOS SORTER - PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Files processed: {summary['counters']['processed']}")
        print(f"Files moved: {summary['counters']['moved']}")
        print(f"Files copied: {summary['counters']['copied']}")
        print(f"Files skipped: {summary['counters']['skipped']}")
        print(f"Videos processed: {summary['counters']['videos_processed']}")
        print(f"Thumbnails processed: {summary['counters']['thumbnails_processed']}")
        print(f"MPG files merged: {summary['counters']['mpg_merged']}")
        print(f"THM files deleted: {summary['counters']['thm_deleted']}")
        print(f"MPG files deleted: {summary['counters']['mpg_deleted']}")
        print(f"Files without date: {summary['counters']['no_date']}")
        print(f"Errors: {summary['counters']['errors']}")
        
        if duration:
            print(f"Duration: {duration:.2f} seconds")
            print(f"Processing rate: {summary['performance']['files_per_second']:.2f} files/second")
        
        if summary['counters']['cache_hits'] + summary['counters']['cache_misses'] > 0:
            print(f"Cache hit rate: {summary['performance']['cache_hit_rate']:.1%}")
        
        print("=" * 60)
        
        if summary['counters']['errors'] == 0:
            print("✅ Processing completed successfully!")
        else:
            print(f"⚠️  Processing completed with {summary['counters']['errors']} errors")
    
    def get_failed_operations(self) -> list:
        """
        Get list of failed operations.
        
        Returns:
            list: List of failed operations
        """
        return [op for op in self._operation_log if not op['success']]
    
    def export_log(self, file_path: Path):
        """
        Export operation log to a file.
        
        Args:
            file_path (Path): Path to export file
        """
        import json
        
        export_data = {
            'summary': self.get_summary(),
            'operations': self._operation_log
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Statistics exported to {file_path}")


def main():
    """Test function for the statistics collector."""
    import time
    
    # Setup basic logging
    logging.basicConfig(level=logging.DEBUG)
    
    collector = StatisticsCollector()
    collector.start_session()
    
    # Simulate some operations
    collector.increment('processed', 5)
    collector.increment('moved', 3)
    collector.increment('copied', 2)
    collector.increment('errors', 1)
    
    time.sleep(1)  # Simulate processing time
    
    collector.end_session()
    collector.print_summary()
    
    # Test export
    export_path = Path("test_stats.json")
    collector.export_log(export_path)
    print(f"Exported to {export_path}")


if __name__ == "__main__":
    main()