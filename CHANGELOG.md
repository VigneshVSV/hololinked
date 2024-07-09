# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- properties are now "observable" and push change events when read or written & value has changed
- input & output JSON schema can be specified for actions, where input schema is used for validation of arguments
- TD has read/write properties' forms at thing level, event data schema
- change log
- some unit tests

### Changed
- events are to specified as descriptors and are not allowed as instance attributes. Specify at class level to 
  automatically obtain a instance specific event.  

### Fixed
- ``class_member`` argument for properties respected more accurately

### Security
- cookie auth will be added

## [v0.1.2] - 2024-06-06

### Added
- first public release to pip, docs are the best source to document this release. Checkout commit 
  [04b75a73c28cab298eefa30746bbb0e06221b81c] and build docs if at all necessary.
 


