# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0] - 2021-08-01
### Added
- Google Drive API library

## [1.0.1] - 2021-08-25
### Added
- virtual environment: env/
- google API folder: google_api/
- scripts to work with venv: run.sh, create_env.sh

### Issue
- [1] paths like '/path/to/my//folder', as these are not being well
  understood by sync() [it splits it out by '/' resulting in an empty field].
- [2] creeateFolderResursively() not returning fileId of the new created folder.
- [3] sync() failing because of the previous mentionded issue.

### Fixed
- bug: don't write paths like '/path/to/my//folder', as these are not being well
       understood by sync() [it splits it out by '/' resulting in an empty field]
       Note this feture could be improved in the future.
- bug: createFolderResursively() not returning fileId of the new created folder.

## This is just a template ...
### Added
### Removed
### Changed
### Deprecated
### Fixed
### Security
