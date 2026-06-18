#!/bin/bash
# ============================================
# 荟城减重 WSP 系统 - 阿里云服务器部署脚本
# ============================================

set -e  # 遇到错误立即退出

# 服务器配置
SERVER_HOST="47.104.220.141"
SERVER_PORT="2023"
SERVER_USER="deployer"
SERVER_PASSWORD="Jjk@ynxt2026"
DEPLOY_DIR="/home/deployer/huicheng-wsp"

echo "======================================"
echo "  荟城减重 WSP 系统 - 阿里云部署"
echo "======================================"
echo ""
echo "📡 服务器: ${SERVER_HOST}:${SERVER_PORT}"
echo "👤 用户: ${SERVER_USER}"
echo "📁 目录: ${DEPLOY_DIR}"
echo ""

# 检查sshpass是否安装
if ! command -v sshpass &> /dev/null; then
    echo "⚠️  sshpass未安装,正在安装..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install sshpass
    else
        sudo apt-get install -y sshpass
    fi
fi

# 检查rsync是否安装
if ! command -v rsync &> /dev/null; then
    echo "❌ rsync未安装,请先安装rsync"
    exit 1
fi

echo "✅ 依赖检查通过"
echo ""

# 第一步:上传代码到服务器
echo "📤 步骤1: 上传代码到服务器..."
echo ""

# 使用rsync同步文件(排除不必要的文件)
sshpass -p "${SERVER_PASSWORD}" rsync -avz --delete \
    -e "ssh -p ${SERVER_PORT} -o StrictHostKeyChecking=no" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='logs/*' \
    --exclude='data/*' \
    --exclude='.env' \
    ./ ${SERVER_USER}@${SERVER_HOST}:${DEPLOY_DIR}/

echo "✅ 代码上传完成"
echo ""

# 第二步:在服务器上执行部署
echo "🚀 步骤2: 在服务器上执行部署..."
echo ""

sshpass -p "${SERVER_PASSWORD}" ssh -p ${SERVER_PORT} -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
#!/bin/bash
set -e

cd /home/deployer/huicheng-wsp

echo "📁 当前目录: $(pwd)"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装,请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装,请先安装Docker Compose"
    exit 1
fi

echo "✅ Docker版本: $(docker --version)"
echo "✅ Docker Compose版本: $(docker-compose --version)"
echo ""

# 创建.env文件(如果不存在)
if [ ! -f .env ]; then
    echo "📝 创建.env配置文件..."
    cp .env.example .env
    
    # 生成随机SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    
    # 修改.env文件中的密钥
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
    
    echo "✅ .env文件已创建"
    echo "⚠️  请手动检查.env文件中的密码配置"
else
    echo "✅ .env文件已存在"
fi

echo ""

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs
mkdir -p data/mysql-backup
mkdir -p data/uploads
mkdir -p ssl
echo "✅ 目录创建完成"
echo ""

# 停止旧容器(如果存在)
echo "🛑 停止旧容器..."
docker-compose down 2>/dev/null || true
echo ""

# 拉取最新镜像
echo "📥 拉取Docker镜像..."
docker-compose pull 2>/dev/null || true
echo ""

# 构建并启动服务
echo "🚀 构建并启动服务..."
docker-compose up -d --build

echo ""
echo "⏳ 等待服务启动(30秒)..."
sleep 30

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "🔍 健康检查..."

# 检查MySQL
if docker-compose exec -T mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD:-root123456} 2>/dev/null | grep -q "alive"; then
    echo "✅ MySQL 运行正常"
else
    echo "⚠️  MySQL 可能还在启动中"
fi

# 检查Web应用
if curl -s http://localhost:5000/api/dashboard > /dev/null 2>&1; then
    echo "✅ Web应用 运行正常"
else
    echo "⚠️  Web应用 可能还在启动中"
fi

echo ""
echo "======================================"
echo "  部署完成！"
echo "======================================"
echo ""
echo "📱 访问地址:"
echo "   http://${SERVER_HOST}:5000"
echo ""
echo "📋 常用命令:"
echo "   查看日志:     docker-compose logs -f"
echo "   重启服务:     docker-compose restart"
echo "   停止服务:     docker-compose down"
echo "   更新应用:     cd ${DEPLOY_DIR} && git pull && docker-compose up -d --build"
echo ""
echo "🔐 安全提示:"
echo "   1. 请立即修改.env文件中的默认密码"
echo "   2. 建议配置防火墙只开放必要端口"
echo "   3. 建议配置HTTPS(参考DEPLOY.md)"
echo ""

ENDSSH

echo ""
echo "✅ 服务器部署完成!"
echo ""
echo "📱 访问地址: http://${SERVER_HOST}:5000"
echo ""
echo "📋 后续操作:"
echo "   1. SSH登录服务器: ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_HOST}"
echo "   2. 查看日志: docker-compose logs -f"
echo "   3. 修改密码: 编辑 ${DEPLOY_DIR}/.env 文件"
echo ""
