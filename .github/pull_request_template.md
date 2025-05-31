## Pull Request Description

### What does this PR do?
A clear and concise description of what this pull request accomplishes.

### Type of Change
Please delete options that are not relevant:
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Test improvements
- [ ] CI/CD improvements

### Related Issues
Fixes #(issue number)
Closes #(issue number)
Related to #(issue number)

## Changes Made

### Summary of Changes
- Change 1
- Change 2
- Change 3

### Files Modified
- `src/module.py` - Description of changes
- `config.yaml.example` - Added new configuration options
- `README.md` - Updated documentation

### New Dependencies
List any new dependencies added:
- `package-name>=version` - Reason for adding

## Testing

### How Has This Been Tested?
Please describe the tests that you ran to verify your changes:
- [ ] Unit tests pass (`make test`)
- [ ] Integration tests pass
- [ ] Manual testing performed
- [ ] Tested on multiple operating systems
- [ ] Tested with different file types

### Test Configuration
- **Operating System:** [e.g. Ubuntu 22.04]
- **Python Version:** [e.g. 3.9.7]
- **Test Files:** [e.g. JPEG photos, MPG videos, THM thumbnails]

### Test Commands Used
```bash
# Commands used to test this change
make test
python run.py --dry-run --source test_data/
python run.py --test-exif sample.jpg
```

### Test Results
```
# Output from test commands
All tests passed: ✓
Files processed: 50
No errors encountered
```

## Code Quality

### Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

### Code Style
- [ ] Code formatted with `black` (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Type hints added where appropriate
- [ ] Docstrings added for new functions/classes

## Documentation

### Documentation Updated
- [ ] README.md updated if needed
- [ ] CHANGELOG.md updated
- [ ] Configuration examples updated
- [ ] Inline code comments added
- [ ] Docstrings updated

### Breaking Changes
If this is a breaking change, please describe:
- What breaks
- How users should update their code/configuration
- Migration guide provided

## Performance Impact

### Performance Considerations
- [ ] No performance impact
- [ ] Performance improved
- [ ] Performance impact acceptable for the feature
- [ ] Performance impact documented

### Benchmarks
If applicable, provide before/after performance measurements:
```
Before: Processing 1000 files in 45 seconds
After:  Processing 1000 files in 38 seconds
```

## Security

### Security Checklist
- [ ] No sensitive data exposed in logs
- [ ] Input validation added where needed
- [ ] External command execution is safe
- [ ] File path validation implemented
- [ ] No hardcoded secrets or paths

## Additional Notes

### Screenshots
If applicable, add screenshots to demonstrate the changes.

### Migration Guide
If this introduces breaking changes, provide migration instructions:
```yaml
# Old configuration
old_option: value

# New configuration
new_section:
  updated_option: value
```

### Future Considerations
Any thoughts on future improvements or related work:
- [ ] Follow-up issue created for enhancement XYZ
- [ ] Documentation could be improved in area ABC
- [ ] Performance could be optimized in module DEF

### Review Focus Areas
Please pay special attention to:
- [ ] Error handling in new feature
- [ ] Configuration validation
- [ ] File path security
- [ ] Memory usage with large file sets
- [ ] Cross-platform compatibility

---

**Note for Reviewers:** 
Please test this PR with your own photo collection using `--dry-run` mode first.