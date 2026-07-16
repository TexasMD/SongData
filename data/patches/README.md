# Data patches

This directory holds small, reviewable data patch manifests that are safe to
track in Git. Generated exports and full local database files stay out of Git
unless explicitly promoted.

Patch manifests should identify the target file, row key, target column, old
value, new value, source review artifact, approval basis, and backup path.
