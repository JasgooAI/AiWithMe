#!/bin/bash
# 情报收集系统安装脚本
# 自动检测项目路径，无需手动配置

set -e

# 获取脚本所在目录，推导项目路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARCHIVE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$ARCHIVE_DIR")"

PLIST_NAME="com.intel-collector.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🚀 情报收集系统安装脚本"
echo "========================"
echo "项目目录: $PROJECT_DIR"
echo ""

# 检查 Python 虚拟环境
if [ ! -d "$ARCHIVE_DIR/.venv" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv "$ARCHIVE_DIR/.venv"
fi

# 安装依赖
echo "安装 Python 依赖..."
"$ARCHIVE_DIR/.venv/bin/pip" install -r "$ARCHIVE_DIR/requirements.txt" -q

# 检查配置文件
if [ ! -f "$ARCHIVE_DIR/.system/config/config.yaml" ]; then
    echo ""
    echo "⚠️  未找到配置文件！"
    echo "请先复制配置模板并填写您的 API 密钥："
    echo ""
    echo "  cp $ARCHIVE_DIR/.system/config/config.yaml.example \\"
    echo "     $ARCHIVE_DIR/.system/config/config.yaml"
    echo ""
    echo "然后编辑 config.yaml 填写 API 配置"
    echo ""
    exit 1
fi

# 确保日志目录存在
mkdir -p "$ARCHIVE_DIR/.system/logs"

# 生成 launchd plist 文件
echo "生成定时任务配置..."

cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.intel-collector</string>

    <key>ProgramArguments</key>
    <array>
        <string>$ARCHIVE_DIR/.venv/bin/python</string>
        <string>$ARCHIVE_DIR/src/main.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>$ARCHIVE_DIR/.system/logs/launchd-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$ARCHIVE_DIR/.system/logs/launchd-stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# 如果已存在，先卸载
if launchctl list 2>/dev/null | grep -q "com.intel-collector"; then
    echo "卸载旧的定时任务..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# 加载任务
launchctl load "$PLIST_DEST"

echo ""
echo "✅ 安装完成！"
echo ""
echo "定时任务已配置为每天 20:00 自动运行"
echo ""
echo "常用命令："
echo "  手动运行:    $ARCHIVE_DIR/.venv/bin/python $ARCHIVE_DIR/src/main.py"
echo "  查看状态:    launchctl list | grep intel"
echo "  手动触发:    launchctl start com.intel-collector"
echo "  查看日志:    cat $ARCHIVE_DIR/.system/logs/launchd-stdout.log"
echo ""
