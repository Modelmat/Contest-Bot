#!/usr/bin/env bash
git checkout release
git pull --no-edit
git merge master release -m "Merge release to master"
git push origin release
git checkout master