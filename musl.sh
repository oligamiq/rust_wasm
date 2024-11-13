#!/bin/sh

# https://github.com/rust-lang/rust/blob/9a9daddd0dacfe8c5e8eaa07cfd054a3631bcde7/src/ci/docker/scripts/musl.sh

#!/bin/sh
set -ex

TAG=$1
shift

# Ancient binutils versions don't understand debug symbols produced by more recent tools.
# Apparently applying `-fPIC` everywhere allows them to link successfully.
export CFLAGS="-fPIC $CFLAGS"

MUSL=musl-1.2.3

# may have been downloaded in a previous run
if [ ! -d $MUSL ]; then
  curl https://www.musl-libc.org/releases/$MUSL.tar.gz | tar xzf -
fi

cd $MUSL
./configure --enable-debug --disable-shared --prefix=/musl-$TAG "$@"
if [ "$TAG" = "i586" -o "$TAG" = "i686" ]; then
  make -j$(nproc) AR=ar RANLIB=ranlib
else
  make -j$(nproc)
fi
sudo make install
make clean
