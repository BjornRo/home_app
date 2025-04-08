#!/bin/sh
# This file exist solely to update the ca-certificates to import my own CA

update-ca-certificates

target_file=$EXE_PATHNAME
tmp_name=${target_file}_tmp

# Move target into tmp, move real target(.bak) to target, delete tmp
mv $target_file $tmp_name
mv ${target_file}.bak $target_file
rm $tmp_name

exit 1
