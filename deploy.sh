#!/bin/bash
# ============================================
# 荟城减重 WSP 系统 - 一键部署脚本
# ============================================

set -e  # 遇到错误立即退出

echo "======================================"
echo "  荟城减重 WSP 系统 - Docker 部署"
echo "======================================"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

echo "✅ Docker版本: $(docker --version)"
echo "✅ Docker Compose版本: $(docker-compose --version)"
echo ""

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo "⚠️  警告: .env文件不存在，从.env.example复制..."
    cp .env.example .env
    echo ""
    echo "📝 请编辑 .env 文件，修改以下配置:"
    echo "   - MYSQL_ROOT_PASSWORD (MySQL root密码)"
    echo "   - MYSQL_PASSWORD (应用数据库密码)"
    echo "   - SECRET_KEY (Flask密钥，使用随机字符串)"
    echo ""
    echo "生成随机密钥命令:"
    echo "   python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo ""
    read -p "按回车键继续部署..."
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs
mkdir -p data/mysql-backup
mkdir -p data/uploads
mkdir -p ssl
echo "✅ 目录创建完成"
echo ""

# 选择部署模式
echo "请选择部署模式:"
echo "1. 基础部署 (MySQL + Flask) - 推荐开发/测试环境"
echo "2. 完整部署 (MySQL + Flask + Nginx) - 推荐生产环境"
read -p "请输入选项 (1/2, 默认1): " deploy_mode

case ${deploy_mode:-1} in
    1)
        echo ""
        echo "🚀 开始基础部署..."
        docker-compose up -d
        ;;
    2)
        echo ""
        echo "🚀 开始完整部署（含Nginx）..."
        docker-compose --profile production up -d
        ;;
    *)
        echo "❌ 无效选项，使用基础部署"
        docker-compose up -d
        ;;
esac

echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "🔍 健康检查..."

# 检查MySQL
if docker-compose exec -T mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD:-root123456} &> /dev/null; then
    echo "✅ MySQL 运行正常"
else
    echo "❌ MySQL 启动失败，请查看日志: docker-compose logs mysql"
fi

# 检查Web应用
if curl -s http://localhost:5000/api/dashboard > /dev/null 2>&1; then
    echo "✅ Web应用 运行正常"
else
    echo "⚠️  Web应用 可能还在启动中，请稍后检查"
fi

echo ""
echo "======================================"
echo "  部署完成！"
echo "======================================"
echo ""
echo "📱 访问地址:"
if [ "${deploy_mode:-1}" = "2" ]; then
    echo "   http://localhost (通过Nginx)"
else
    echo "   http://localhost:5000"
fi
echo ""
echo "📋 常用命令:"
echo "   查看日志:     docker-compose logs -f"
echo "   重启服务:     docker-compose restart"
echo "   停止服务:     docker-compose down"
echo "   更新应用:     git pull && docker-compose up -d --build"
echo ""
echo "📖 详细文档: 查看 DEPLOY.md"
echo ""
