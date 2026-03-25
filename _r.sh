#!/bin/bash
output_file="output.txt" > "$output_file"

# 제외할 폴더 리스트 (경로 앞뒤에 * 가능)
EXCLUDED_DIRS=( "*/node_modules/*" "*/volume/*" "*/__pycache__/*" "*/venv/*" "*/volumes/*" "*/db_data/*" "*/.gradle/*" "*/build/*" "*/gradle/*" "*/.idea/*" "*/_docs/*" "*/.vscode/*" "*/.git/*" "*/docs/*" "*/venv/*" "*/templates/*")
# 제외할 확장자 리스트 (대소문자 구분 없이 제외)
EXCLUDED_EXTS=("ico" "env" "png" "jpg" "sh" "md" "txt" "html" "json" "log")
# 제외할 파일 이름 (정확한 이름 일치)
EXCLUDED_FILES=(".DS_Store" ".gitignore" "$output_file" "r.sh" "gradlew" "gradlew.bat" "setting.gradle")

# find 조건문 동적 생성
FIND_CMD=(find .)
# 제외할 디렉토리 추가
for dir in "${EXCLUDED_DIRS[@]}"; do
  FIND_CMD+=( -path "$dir" -o )
done
# 괄호 닫기 및 prune
FIND_CMD=( "${FIND_CMD[@]:0:${#FIND_CMD[@]}-1}" )  # 마지막 -o 제거
FIND_CMD=( "${FIND_CMD[@]}" -prune -o -type f )
# 제외할 확장자 조건 추가
for ext in "${EXCLUDED_EXTS[@]}"; do
  FIND_CMD+=( ! -iname "*.${ext}" )
done
# 제외할 파일 이름 조건 추가
for file in "${EXCLUDED_FILES[@]}"; do
  FIND_CMD+=( ! -name "$file" )
done
# 출력 조건
FIND_CMD+=( -print )
# 실행 및 출력 처리
"${FIND_CMD[@]}" | while read -r file; do
  {
    echo '```'
    echo "$file"
    echo
    cat "$file"
    echo
    echo '```'
    echo
  } >> "$output_file"
done
echo ":package: Success! -> $output_file"