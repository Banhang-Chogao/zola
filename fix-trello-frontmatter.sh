#!/usr/bin/env bash
set -euo pipefail

add_fm() {
  file="$1"
  title="$2"
  desc="$3"
  slug="$4"
  tags="$5"

  if head -n 1 "$file" | grep -qE '^(\+\+\+|---)$'; then
    echo "SKIP: $file already has frontmatter"
    return
  fi

  cp "$file" "$file.bak-frontmatter"
  tmp="$(mktemp)"

  cat > "$tmp" <<EOF
+++
title = "$title"
date = 2026-06-22
description = "$desc"
slug = "$slug"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = $tags

[extra]
featured = false
+++

EOF

  cat "$file" >> "$tmp"
  mv "$tmp" "$file"
  echo "FIXED: $file"
}

add_fm \
"content/posting/loc-card-den-han-focus-time-trello-mobile.md" \
"Lọc card đến hạn trong Trello Mobile" \
"Hướng dẫn lọc card đến hạn trong Trello Mobile để dễ theo dõi công việc, ưu tiên việc cần xử lý và quản lý deadline hiệu quả hơn." \
"loc-card-den-han-focus-time-trello-mobile" \
'["Trello", "Trello Mobile", "Focus Time", "quản lý công việc", "deadline"]'

add_fm \
"content/posting/card-due-date-hien-trong-trello-planner.md" \
"Card due date trong Trello Planner" \
"Giải thích cách card due date hiển thị trong Trello Planner, giúp người dùng theo dõi hạn chót và quản lý lịch làm việc rõ ràng hơn." \
"card-due-date-hien-trong-trello-planner" \
'["Trello", "Trello Planner", "due date", "quản lý deadline", "productivity"]'

add_fm \
"content/posting/trello-planner-vs-calendar-view-vs-google-calendar.md" \
"Trello Planner, Calendar View và Google Calendar" \
"So sánh Trello Planner, Calendar View và Google Calendar để chọn cách quản lý lịch, deadline và công việc phù hợp trên mobile." \
"trello-planner-vs-calendar-view-vs-google-calendar" \
'["Trello", "Trello Planner", "Calendar View", "Google Calendar", "quản lý lịch"]'
