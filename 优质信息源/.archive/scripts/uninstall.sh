#!/bin/bash
# 情报收集系统卸载脚本

PLIST_NAME="com.intel-collector.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🗑️  情报收集系统卸载脚本"
echo "========================"

# 停止并卸载 launchd 任务
if launchctl list | grep -q "com.intel-collector"; then
    echo "停止定时任务..."
    launchctl stop com.intel-collector 2>/dev/null || true
    echo "卸载定时任务..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# 删除 plist 文件
if [ -f "$PLIST_PATH" ]; then
    rm "$PLIST_PATH"
    echo "已删除 plist 文件"
fi

echo ""
echo "✅ 卸载完成！"
echo ""
echo "注意: 项目文件和数据未被删除"
echo "如需完全删除，请手动删除项目目录"
echo ""
