import os
import sys
import subprocess
import platform
import urllib.request
import tempfile

def download_file(url, filename):
    """下载文件"""
    print(f"正在下载 {filename}...")
    urllib.request.urlretrieve(url, filename)
    print(f"{filename} 下载完成！")

def install_windows_python():
    """安装Windows Python"""
    print("正在安装Windows Python...")
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        python_installer = os.path.join(temp_dir, "python_installer.exe")
        
        # 下载Python安装程序
        python_url = "https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe"
        download_file(python_url, python_installer)
        
        # 使用Wine安装Python
        subprocess.run([
            'wine', python_installer,
            '/quiet',  # 静默安装
            'InstallAllUsers=1',  # 为所有用户安装
            'PrependPath=1',  # 添加到PATH
            'Include_test=0',  # 不包含测试
        ], check=True)
        
        # 清理临时文件
        os.remove(python_installer)
        os.rmdir(temp_dir)
        
        print("Windows Python安装完成！")
        return True
    except Exception as e:
        print(f"错误：安装Windows Python失败 - {str(e)}")
        return False

def check_wine():
    """检查是否安装了Wine"""
    try:
        subprocess.run(['wine', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def install_wine_macos():
    """在macOS上安装Wine"""
    if platform.system() == 'Darwin':  # macOS
        print("正在安装Wine...")
        try:
            # 使用Homebrew安装Wine
            subprocess.run(['brew', 'install', 'wine-stable'], check=True)
            print("Wine安装成功！")
            return True
        except subprocess.SubprocessError:
            print("错误：无法安装Wine。请确保已安装Homebrew。")
            return False
    return False

def setup_windows_python():
    """设置Windows Python环境"""
    print("正在设置Windows Python环境...")
    try:
        # 检查Python是否已安装
        try:
            subprocess.run(['wine', 'python', '--version'], capture_output=True, check=True)
        except subprocess.SubprocessError:
            # 如果Python未安装，则安装它
            if not install_windows_python():
                return False
        
        # 使用Wine安装Python包
        subprocess.run(['wine', 'python', '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run(['wine', 'python', '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("Windows Python环境设置完成！")
        return True
    except subprocess.SubprocessError as e:
        print(f"错误：无法设置Windows Python环境 - {str(e)}")
        return False

def build_windows_exe():
    """构建Windows可执行文件"""
    print("开始构建Windows可执行文件...")
    try:
        # 准备命令行参数
        if platform.system() == 'Windows':
            base_cmd = [sys.executable]
        else:
            base_cmd = ['wine', 'python']
            
        params = base_cmd + [
            '-m', 'PyInstaller',
            'test.py',
            '--name=HIS导出到用友工具',
            '--windowed',
            '--onefile',
            '--clean',
            '--noconfirm',
            '--add-data=requirements.txt;.',
            '--target-arch=x64',
            '--uac-admin',
            '--noconsole',
            '--add-data=lib;lib',
        ]

        # 添加隐藏导入
        hidden_imports = [
            'pandas',
            'openpyxl',
            'PyQt5',
            'PyQt5.QtCore',
            'PyQt5.QtGui',
            'PyQt5.QtWidgets',
        ]

        for imp in hidden_imports:
            params.append(f'--hidden-import={imp}')

        # 如果有图标文件，添加图标参数
        if os.path.exists('icon.ico'):
            params.append('--icon=icon.ico')

        subprocess.run(params, check=True)
        print("Windows可执行文件构建完成！")
        print(f"可执行文件位于: {os.path.join('dist', 'Excel合并工具.exe')}")
        return True
    except subprocess.SubprocessError as e:
        print(f"错误：构建Windows可执行文件失败 - {str(e)}")
        return False

def main():
    print("开始打包过程...")
    
    # 检查操作系统
    if platform.system() not in ['Darwin', 'Windows']:
        print("错误：此脚本仅支持macOS和Windows系统！")
        return

    # 在macOS上检查并安装Wine
    if platform.system() == 'Darwin':
        if not check_wine():
            if not install_wine_macos():
                return
        if not setup_windows_python():
            return

    # 构建Windows可执行文件
    if not build_windows_exe():
        return

    print("打包过程完成！")

if __name__ == "__main__":
    main()