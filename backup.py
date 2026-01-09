import os 
import subprocess
import dotenv
import logging
import time
import json
import requests

print("-"*50)
print("Bitwarden Auto Backup Script") 
print("-"*50)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 检查是否存在.env文件
if os.path.exists(".env"):
    dotenv.load_dotenv()
else:
    logging.warning(f".env file not found. Using system environment variables.")    

# 从环境变量中获取
BW_SERVER = os.getenv("BW_SERVER")
BW_USERNAME = os.getenv("BW_USERNAME")
BW_PASSWORD = os.getenv("BW_PASSWORD")

# 简单的命令运行函数
def run(cmd, capture=True):
    """运行命令，返回结果对象"""
    logging.debug(f"执行: {cmd}")
    return subprocess.run(
        cmd, 
        shell=isinstance(cmd, str),
        capture_output=capture, 
        text=True,
        check=False
    )

def upload_cloud(backup_file):
    """上传备份文件到云存储"""
    try:
        # 获取环境变量
        webdav_url = os.getenv("WEBDAV_URL", "").rstrip("/")
        username = os.getenv("WEBDAV_USER", "")
        password = os.getenv("WEBDAV_PASSWORD", "")
        
        if not all([webdav_url, username, password]):
            logging.error("WebDAV环境变量配置不完整")
            return False
        
        # 获取文件的绝对路径
        abs_backup_file = os.path.abspath(backup_file)
        if not os.path.exists(abs_backup_file):
            logging.error(f"备份文件不存在: {abs_backup_file}")
            return False
        
        # 提取文件名
        filename = os.path.basename(backup_file)
        
        # 构建远程路径
        remote_path = f"backups/{filename}"  # 你原来的路径 
        full_url = f"{webdav_url}/{remote_path}"
        
        # 读取文件内容
        with open(abs_backup_file, 'rb') as f:
            file_content = f.read()
        
        # 直接使用requests PUT上传
        response = requests.put(
            full_url,
            data=file_content,
            auth=(username, password),
            headers={
                'User-Agent': 'PythonBackup/1.0',
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(len(file_content))
            },
            timeout=30
        )
        
        # 检查响应
        if response.status_code in [200, 201, 204]:
            logging.info(f"✓ 备份文件上传到云存储成功: {backup_file} -> {remote_path}")
            return True
        else:
            logging.error(f"上传失败 [{response.status_code}]: {response.text[:200]}")
            return False
            
    except Exception as e:
        logging.error(f"上传备份文件到云存储失败: {e}")
        return False

def email_notify(backup_file=None, success=True, error_msg=None):
    """发送邮件通知"""
    try:
        req_url = os.getenv("SMTP2API_URL", "").rstrip("/")
        token = os.getenv("SMTP2API_TOKEN", "")
        to_email = os.getenv("BW_USERNAME", "")
        
        if not all([req_url, token, to_email]):
            logging.error("SMTP2API环境变量配置不完整")
            return False
        
        # 构建邮件内容
        if success:
            if backup_file and os.path.exists(backup_file):
                file_size = os.path.getsize(backup_file)
                file_size_kb = file_size / 1024.0
                file_size_mb = file_size_kb / 1024.0
                
                if file_size_mb >= 1:
                    size_str = f"{file_size_mb:.1f} MB"
                else:
                    size_str = f"{file_size_kb:.1f} KB"
                    
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <h2 style="color: #2c3e50;">Bitwarden 备份成功</h2>
                    <p>Bitwarden 密码库备份任务已成功完成。</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h3 style="color: #28a745; margin-top: 0;">备份详情</h3>
                        <ul style="list-style-type: none; padding-left: 0;">
                            <li><strong>- 备份文件：</strong>{backup_file}</li>
                            <li><strong>- 文件大小：</strong>{size_str} ({file_size} 字节)</li>
                            <li><strong>- 备份时间：</strong>{time.strftime('%Y-%m-%d %H:%M:%S')}</li>
                        </ul>
                    </div>
                    
                    <div style="background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h3 style="color: #17a2b8; margin-top: 0;">备份统计</h3>
                        <p>如需查看详细的备份统计信息，请登录服务器查看备份文件。</p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        此邮件由 Bitwarden 自动备份系统发送<br>
                        请勿回复此邮件
                    </p>
                </body>
                </html>
                """
                subject = f"Bitwarden 备份成功 - {time.strftime('%Y-%m-%d %H:%M')}"
            else:
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <h2 style="color: #2c3e50;">Bitwarden 备份成功</h2>
                    <p>Bitwarden 密码库备份任务已成功完成。</p>
                    <p>备份时间：{time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </body>
                </html>
                """
                subject = f"Bitwarden 备份成功 - {time.strftime('%Y-%m-%d')}"
        else:
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #dc3545;">Bitwarden 备份失败</h2>
                <p>Bitwarden 密码库备份任务执行失败。</p>
                
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #721c24; margin-top: 0;">错误信息</h3>
                    <p style="color: #721c24;">{error_msg or '未知错误'}</p>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #856404; margin-top: 0;">需要处理</h3>
                    <p>请立即检查备份系统，确保密码库安全。</p>
                </div>
                
                <p><strong>失败时间：</strong>{time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    此邮件由 Bitwarden 自动备份系统发送<br>
                    请勿回复此邮件
                </p>
            </body>
            </html>
            """
            subject = f"Bitwarden 备份失败 - {time.strftime('%Y-%m-%d %H:%M')}"
        
        # 构建请求数据
        payload = {
            "to": to_email,
            "subject": subject,
            "html": html_content,  # 使用 html 字段
            "nickname": "Bitwarden 备份系统"
        }
        
        # 可选的文本备用
        text_content = "Bitwarden 备份通知" if success else f"Bitwarden 备份失败: {error_msg}"
        payload["text"] = text_content
        
        logging.info(f"发送邮件通知到: {to_email}")
        
        # 发送请求
        response = requests.post(
            req_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            status_msg = "成功" if success else "失败警告"
            logging.info(f"✓ 邮件通知发送{status_msg}")
            return True
        else:
            logging.error(f"邮件发送失败 [{response.status_code}]: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error("邮件通知请求超时")
        return False
    except requests.exceptions.ConnectionError:
        logging.error("邮件通知连接错误")
        return False
    except Exception as e:
        logging.error(f"发送邮件通知失败: {e}")
        return False

def backup():
    """备份Bitwarden密码库"""
    backup_file = None
    try:
        # 1. 直接配置服务器（无需登出，因为是CI新环境）
        logging.info(f"配置服务器: {BW_SERVER}")
        result = run(["bw", "config", "server", BW_SERVER])
        if result.returncode != 0:
            logging.error(f"配置服务器失败: {result.stderr}")
            email_notify(success=False, error_msg=f"配置服务器失败: {result.stderr[:200]}")
            exit(1)
        logging.info("✓ 服务器配置成功")
        
        # 2. 直接登录并获取session key
        logging.info("登录中...")
        # --raw参数直接输出session key
        result = run(f'bw login {BW_USERNAME} {BW_PASSWORD} --raw')    
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "登录失败"
            logging.error(f"登录失败: {error_msg}")
            email_notify(success=False, error_msg=f"登录失败: {error_msg[:200]}")
            exit(1)
        
        session_key = result.stdout.strip()
        logging.info(f"✓ 登录成功")
        
        # 3. 导出备份
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{timestamp}.json"
        logging.info(f"导出备份: {backup_file}")
        
        result = run(f'bw export --output "{backup_file}" --format json --session "{session_key}"')
        if result.returncode == 0:
            logging.info(f"✓ 备份完成: {backup_file}")
            
            # 显示备份信息
            if os.path.exists(backup_file):
                file_size = os.path.getsize(backup_file)
                logging.info(f"备份文件大小: {file_size} bytes ({file_size/1024:.1f} KB)")
                
                # 验证备份文件格式
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        items_count = len(data.get('items', []))
                        logging.info(f"备份包含项目数: {items_count}")
                        
                        # 上传到云存储
                        upload_success = upload_cloud(backup_file)
                        
                        # 构建详细备份信息
                        backup_info = f"""
备份文件: {backup_file}
文件大小: {file_size} bytes ({file_size/1024:.1f} KB)
项目数量: {items_count}
备份时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
云存储状态: {'成功' if upload_success else '失败'}
                        """
                        
                        # 发送成功邮件通知
                        email_notify(backup_file=backup_file, success=True)
                        
                except json.JSONDecodeError as e:
                    error_msg = f"备份文件格式错误: {str(e)[:200]}"
                    logging.error(error_msg)
                    email_notify(success=False, error_msg=error_msg)
                    exit(1)
                except Exception as e:
                    error_msg = f"处理备份文件时出错: {str(e)[:200]}"
                    logging.error(error_msg)
                    email_notify(success=False, error_msg=error_msg)
                    exit(1)
        else:
            error_msg = result.stderr[:500] if result.stderr else "导出备份失败"
            logging.error(f"导出失败: {error_msg}")
            
            # 发送失败邮件通知
            email_notify(success=False, error_msg=error_msg)
            exit(1)
        
        logging.info("✓ Bitwarden 备份任务完成")
        
    except Exception as e:
        error_msg = str(e)[:500]
        logging.error(f"程序执行失败: {error_msg}")
        
        # 发送异常邮件通知
        email_notify(success=False, error_msg=error_msg)
        exit(1)

if __name__ == "__main__":
    backup()