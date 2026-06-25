#!/bin/bash
git add .
msg="Update: $(date)"
if [ -n "$1" ]; then
    msg="$1"
fi
git commit -m "$msg"
git push -u origin main
echo "Đã đẩy lên GitHub thành công!"
