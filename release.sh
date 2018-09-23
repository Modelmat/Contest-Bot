#!/usr/bin/env bash
git checkout release
git pull --no-edit
git merge master release
git push origin release
git checkout master