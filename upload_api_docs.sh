#!/usr/bin/env bash
set -e
cp server/schema/cloudreactor-openapi3.yml ../api-docs
pushd .
cd ../api-docs
git add cloudreactor-openapi3.yml
git commit -m "Update schema"
git push
popd
