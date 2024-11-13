#!/usr/bin/env bash

set -ex

if [ $UID -eq 0 ]; then
    exec su rustbuild -c "$0"
fi

mkdir build
cd build
cp ../crosstool.defconfig .config
ct-ng olddefconfig
ct-ng build
cd ..
rm -rf build
