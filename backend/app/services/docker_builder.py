"""
Docker 镜像构建服务
"""
import asyncio
import logging
import os
import tarfile
import tempfile
import hashlib
import subprocess
from datetime import datetime
from typing import Optional
import shutil

from app.core.config import settings
from app.services.task_manager import task_manager
from app.services.storage import get_storage
from app.api.schemas import TaskStatus

logger = logging.getLogger(__name__)


class DockerBuilder:
    """Docker 镜像构建器"""

    def __init__(self):
        self._initialized = False

    def _ensure_init(self):
        """确保 Docker 客户端已初始化（使用 subprocess 检查）"""
        if not self._initialized:
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info("Docker 连接成功")
                    self._initialized = True
                else:
                    logger.error(f"Docker info 失败: {result.stderr}")
                    raise RuntimeError("Docker 服务不可用，请确保 Docker 已启动")
            except subprocess.TimeoutExpired:
                logger.error("Docker 连接超时")
                raise RuntimeError("Docker 连接超时，请确保 Docker 已启动")
            except FileNotFoundError:
                logger.error("未找到 docker 命令，请确保 Docker 已安装")
                raise RuntimeError("未找到 docker 命令，请确保 Docker 已安装")
    
    async def build_image(self, task_id: str):
        """
        构建 Docker 镜像（异步执行）
        
        Args:
            task_id: 任务ID
        """
        await task_manager.add_log(task_id, "info", "=" * 50)
        await task_manager.add_log(task_id, "info", "开始构建 Docker 镜像...")

        try:
            # 检查 Docker
            self._ensure_init()
            
            # 获取任务信息
            task = await task_manager.get_task(task_id)
            if not task:
                raise ValueError("任务不存在")
            
            # 创建临时工作目录
            work_dir = os.path.join(settings.BUILD_WORKDIR, task_id)
            os.makedirs(work_dir, exist_ok=True)
            
            await task_manager.add_log(task_id, "info", f"工作目录: {work_dir}")
            
            # 下载 Dockerfile
            await task_manager.add_log(task_id, "info", "下载 Dockerfile...")
            dockerfile_content = await self._download_file(task.dockerfile_key)
            dockerfile_path = os.path.join(work_dir, "Dockerfile")
            with open(dockerfile_path, 'wb') as f:
                f.write(dockerfile_content)
            
            await task_manager.add_log(task_id, "success", "Dockerfile 已就绪")
            
            # 记录 FROM 行用于调试
            from_lines = [l for l in dockerfile_content.decode().split('\n') if l.strip().upper().startswith('FROM ')]
            await task_manager.add_log(task_id, "info", f"原始 FROM: {from_lines[:3]}")
            
            # 自动修复 Dockerfile 中的 FROM 指令，确保与目标架构匹配
            dockerfile_content = await self._fix_dockerfile_arch(dockerfile_content, task.target_arch)
            
            fixed_from_lines = [l for l in dockerfile_content.decode().split('\n') if l.strip().upper().startswith('FROM ')]
            await task_manager.add_log(task_id, "info", f"修复后 FROM: {fixed_from_lines[:3]}")
            dockerfile_path = os.path.join(work_dir, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content.decode('utf-8') if isinstance(dockerfile_content, bytes) else dockerfile_content)
            
            await task_manager.add_log(task_id, "info", f"Dockerfile 已调整为 {task.target_arch} 架构")
            context_path = None
            if task.context_key:
                await task_manager.add_log(task_id, "info", "下载构建上下文...")
                context_content = await self._download_file(task.context_key)
                
                # 解压到临时目录
                context_extracted = os.path.join(work_dir, "context")
                os.makedirs(context_extracted, exist_ok=True)
                
                # 根据文件类型解压
                context_name = task.context_name or "context.tar"
                if context_name.endswith('.zip'):
                    await self._unzip(context_content, context_extracted)
                else:
                    await self._untar(context_content, context_extracted)
                
                context_path = context_extracted
                await task_manager.add_log(task_id, "success", "构建上下文已解压")
            
            # 确定构建上下文目录
            build_context = context_path or work_dir

            # 检查 BuildKit 支持
            await task_manager.add_log(task_id, "info", f"目标架构: {task.target_arch}")

            # 构建镜像
            await task_manager.add_log(task_id, "info", "开始构建镜像（这可能需要几分钟）...")

            # 使用用户指定的镜像名和版本，如果没有则使用默认值
            if task.image_name:
                # 清理镜像名中的非法字符
                safe_name = task.image_name.lower().replace('_', '-').replace('_', '-')
                safe_name = ''.join(c if c.isalnum() or c in '.-_' else '' for c in safe_name)
                image_tag = f"{safe_name}:{task.image_tag or 'latest'}"
            else:
                image_tag = f"build-{task_id[:8]}:latest"

            await task_manager.add_log(task_id, "info", f"镜像标签: {image_tag}")

            # 使用 Docker BuildKit 进行跨架构构建
            success = await self._build_with_buildx(
                task_id=task_id,
                dockerfile_path=dockerfile_path,
                build_context=build_context,
                target_arch=task.target_arch,
                image_tag=image_tag
            )
            
            if success:
                # 导出镜像为 tar
                await task_manager.add_log(task_id, "info", "导出镜像...")
                tar_path = await self._export_image(
                    task_id=task_id,
                    image_tag=image_tag,
                    target_arch=task.target_arch
                )

                # 上传到存储（使用异步方法避免阻塞）
                await task_manager.add_log(task_id, "info", "上传镜像...")
                result_key = f"results/{task_id}/{task.target_arch.split('/')[-1]}.tar"

                with open(tar_path, 'rb') as f:
                    tar_content = f.read()

                storage = get_storage()
                upload_success = await storage.upload_file_async(
                    key=result_key,
                    content=tar_content,
                    content_type="application/x-tar"
                )

                # 检查上传结果
                if not upload_success:
                    raise RuntimeError(f"文件上传失败: {result_key}")
                
                # 更新任务状态
                await task_manager.set_result(task_id, result_key)
                await task_manager.add_log(
                    task_id, 
                    "success", 
                    f"镜像已上传: {result_key}"
                )
                
                # 清理
                await self._cleanup(work_dir, tar_path)
                
            else:
                raise RuntimeError("镜像构建失败")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"构建失败: {e}")
            
            # 检测网络问题并提供更清晰的错误提示
            if any(keyword in error_msg.lower() for keyword in [
                "deadline", "timeout", "connection refused", 
                "network", "registry", "docker.io", "resolve",
                "eof", "no such host", "registry-1"
            ]):
                error_hint = (
                    "\n\n========== Docker Hub 连接问题 ==========\n"
                    "可能是网络问题导致无法访问 Docker Hub。\n\n"
                    "请按以下步骤解决：\n"
                    "1. 编辑 /etc/docker/daemon.json 添加 registry mirrors:\n"
                    "   {\n"
                    '     "registry-mirrors": [\n'
                    '       "https://docker.1panel.live",\n'
                    '       "https://docker.m.daocloud.io",\n'
                    '       "https://docker-cf.registry.cyou"\n'
                    "     ]\n"
                    "   }\n\n"
                    "2. 重启 Docker 服务：sudo systemctl restart docker\n\n"
                    "3. 或检查网络和 DNS 配置\n"
                    "===========================================\n"
                )
                error_msg = f"{error_msg}\n{error_hint}"
                await task_manager.add_log(task_id, "warning", error_hint)
            
            await task_manager.set_error(task_id, error_msg)
            await task_manager.add_log(task_id, "error", f"构建失败: {error_msg}")
    
    async def _build_with_buildx(
        self,
        task_id: str,
        dockerfile_path: str,
        build_context: str,
        target_arch: str,
        image_tag: str
    ) -> bool:
        """
        使用 Docker BuildX 进行跨架构构建
        
        Args:
            task_id: 任务ID
            dockerfile_path: Dockerfile 路径
            build_context: 构建上下文路径
            target_arch: 目标架构
            image_tag: 镜像标签
        
        Returns:
            是否成功
        """
        await task_manager.add_log(task_id, "info", "检查 BuildX 环境...")
        
        # 国内镜像源列表
        registry_mirrors = [
            "docker-0.unsee.tech",
            "docker-cf.registry.cyou",
            "docker.1panel.live",
            "docker.m.daocloud.io"
        ]
        
        # 为 BuildKit 创建 registry mirrors 配置
        # BuildKit 不读 daemon.json，需要单独的 /etc/buildkitd.toml
        buildkitd_config_path = await self._setup_buildkit_config(registry_mirrors)
        
        # 检查 BuildX 是否可用
        try:
            result = subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("BuildX 不可用")
            await task_manager.add_log(task_id, "info", f"BuildX 版本: {result.stdout.split()[2]}")
        except Exception as e:
            await task_manager.add_log(task_id, "error", f"BuildX 检查失败: {e}")
            raise RuntimeError(f"BuildX 不可用: {e}")
        
        # 创建或使用现有的 builder
        builder_name = "docker-build-builder"
        
        # 构建 buildx create 命令
        # 注意：必须使用 docker-container driver 才能让 buildkitd 读取 buildkitd.toml 中的 registry mirrors
        create_cmd = [
            "docker", "buildx", "create",
            "--name", builder_name,
            "--driver", "docker-container",  # 必须用这个 driver 才能用 registry mirrors
            "--use"
        ]
        
        # 如果成功配置了 buildkitd.toml，添加配置路径
        if buildkitd_config_path:
            create_cmd.extend(["--buildkitd-config", buildkitd_config_path])
        
        await task_manager.add_log(task_id, "info", f"创建 BuildX builder...")
        
        # 先尝试使用现有 builder
        subprocess.run(
            ["docker", "buildx", "use", builder_name],
            capture_output=True
        )
        
        # 先尝试销毁现有 builder（确保配置生效）
        subprocess.run(
            ["docker", "buildx", "rm", "-f", builder_name],
            capture_output=True
        )
        
        # 创建新的 builder（会应用新的 registry mirrors）
        create_result = subprocess.run(
            create_cmd,
            capture_output=True, text=True, timeout=30
        )
        
        if create_result.returncode != 0:
            stderr = create_result.stderr.lower()
            # 如果 builder 已存在，忽略错误
            if "already exists" not in stderr:
                await task_manager.add_log(task_id, "warning", f"创建 builder 警告: {create_result.stderr[:200]}")
        
        await task_manager.add_log(task_id, "info", "BuildX builder 已就绪")
        
        # 构建命令
        build_cmd = [
            "docker", "buildx", "build",
            "--platform", target_arch,
            "--tag", image_tag,
            "--load",  # 加载到本地 Docker
            "-f", dockerfile_path,
            build_context,
        ]
        
        build_env = {
            "DOCKER_BUILDKIT": "1",
            "BUILDKIT_PROGRESS": "plain"
        }
        
        await task_manager.add_log(task_id, "info", f"目标架构: {target_arch}")
        await task_manager.add_log(task_id, "info", "使用 registry mirrors: " + ", ".join(registry_mirrors))
        await task_manager.add_log(task_id, "info", "开始构建镜像（这可能需要几分钟）...")
        await task_manager.add_log(task_id, "info", f"镜像标签: {image_tag}")
        
        # 构建超时设置（从配置读取，转换为秒）
        BUILD_TIMEOUT = settings.BUILD_TIMEOUT_MINUTES * 60
        await task_manager.add_log(task_id, "info", f"构建超时时间: {settings.BUILD_TIMEOUT_MINUTES} 分钟")
        
        # 使用 tee 来同时显示和捕获输出，同时设置 BUILDKIT_PROGRESS=plain
        build_env = {
            "DOCKER_BUILDKIT": "1",
            "BUILDKIT_PROGRESS": "plain"
        }
        
        # 创建进程
        process = await asyncio.create_subprocess_exec(
            *build_cmd,
            env={**os.environ, **build_env},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # 合并 stderr 到 stdout
            cwd=build_context
        )
        
        # 实时读取输出的协程
        all_output = []  # 保存所有输出用于后续错误分析
        
        async def read_output(stream):
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    
                    line_text = line.decode('utf-8', errors='replace').rstrip()
                    if not line_text:
                        continue
                    
                    all_output.append(line_text)
                    
                    # 根据内容类型选择日志级别
                    lower_line = line_text.lower()
                    if any(kw in lower_line for kw in ['error', 'failed', 'fatal']):
                        await task_manager.add_log(task_id, "error", line_text[:200])
                    elif any(kw in lower_line for kw in ['warn', 'warning']):
                        await task_manager.add_log(task_id, "warning", line_text[:200])
                    elif 'step' in lower_line and ('#' in line_text):
                        # Docker 构建步骤 - 重要信息
                        await task_manager.add_log(task_id, "info", line_text[:200])
                    else:
                        await task_manager.add_log(task_id, "info", line_text[:200])
                        
            except Exception as e:
                logger.error(f"读取输出流失败: {e}")
        
        # 并行执行构建和读取输出
        read_task = asyncio.create_task(read_output(process.stdout))
        
        try:
            exit_code = await asyncio.wait_for(
                process.wait(),
                timeout=BUILD_TIMEOUT
            )
            
            # 确保输出读取完成
            await asyncio.wait_for(read_task, timeout=5)
            
        except asyncio.TimeoutError:
            await task_manager.add_log(task_id, "error", f"构建超时（{BUILD_TIMEOUT}秒），终止进程")
            process.kill()
            await process.wait()
            read_task.cancel()
            return False
        
        # 检测 Docker Hub 连接错误并提供解决建议
        hub_errors = [
            ("registry-1.docker.io", "Docker Hub 连接失败。请配置 registry 镜像或重启 Docker 服务。"),
            ("timeout", "连接超时，请检查网络或配置 registry 镜像。"),
            ("EOF", "Docker Hub 连接异常中断，请重启 Docker 服务或配置 registry 镜像。"),
            ("no such host", "无法解析 Docker Hub 域名，请检查 DNS 配置。"),
        ]
        
        full_output_text = '\n'.join(all_output).lower()
        for error_pattern, hint in hub_errors:
            if error_pattern.lower() in full_output_text:
                await task_manager.add_log(task_id, "warning", hint)
                await task_manager.add_log(task_id, "warning", 
                    "解决方案：\n"
                    "1) 配置 Docker daemon registry mirrors（编辑 /etc/docker/daemon.json）\n"
                    "2) 或配置 BuildKit（编辑 /etc/buildkitd.toml）\n"
                    "3) 重启 Docker 服务：sudo systemctl restart docker\n"
                    "4) 检查网络连接和 DNS 设置")
                break
        
        return exit_code == 0
    
    async def _export_image(
        self,
        task_id: str,
        image_tag: str,
        target_arch: str
    ) -> str:
        """导出镜像为 tar 文件"""
        arch_name = target_arch.split('/')[-1]
        tar_path = os.path.join(
            settings.result_dir,
            f"{task_id}_{arch_name}.tar"
        )
        os.makedirs(settings.result_dir, exist_ok=True)
        
        # 导出超时设置（5分钟）
        EXPORT_TIMEOUT = 300
        
        # 使用 docker save 导出
        cmd = ["docker", "save", "-o", tar_path, image_tag]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=EXPORT_TIMEOUT
            )
        except asyncio.TimeoutError:
            await task_manager.add_log(task_id, "error", f"导出超时（{EXPORT_TIMEOUT}秒），终止进程")
            process.kill()
            await process.wait()
            raise RuntimeError("导出镜像超时")
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "导出失败"
            await task_manager.add_log(task_id, "error", f"导出镜像失败: {error_msg}")
            raise RuntimeError(f"导出镜像失败: {error_msg}")
        
        await task_manager.add_log(task_id, "success", f"镜像已导出: {tar_path}")
        
        # 清理镜像
        try:
            await asyncio.create_subprocess_exec("docker", "rmi", image_tag)
        except:
            pass
        
        return tar_path
    
    async def _download_file(self, key: str) -> bytes:
        """下载文件（异步）"""
        storage = get_storage()

        try:
            content = await storage.download_file_async(key)
            if content is not None:
                return content
        except Exception as e:
            logger.error(f"下载文件失败: {e}")

        raise FileNotFoundError(f"文件不存在: {key}")
    
    async def _fix_dockerfile_arch(self, content: bytes, target_arch: str) -> bytes:
        """
        自动修复 Dockerfile 中的 FROM 指令架构
        
        Args:
            content: Dockerfile 内容
            target_arch: 目标架构（如 linux/amd64, linux/arm64）
        
        Returns:
            修复后的 Dockerfile 内容
        """
        text = content.decode('utf-8') if isinstance(content, bytes) else content
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 检测 FROM 指令
            if stripped.upper().startswith('FROM '):
                import re
                
                # 匹配 FROM [--platform=xxx] image[:tag][@digest] [AS alias]
                match = re.match(
                    r'^FROM\s+(?:--platform=([^\s]+)\s+)?(\S+)(?:\s+AS\s+\S+)?',
                    stripped,
                    re.IGNORECASE
                )
                
                if match:
                    platform = match.group(1)
                    
                    # 只修复硬编码的平台值
                    if platform and platform not in ('${TARGETARCH}', '${BUILDARCH}'):
                        line = line.replace(f'--platform={platform}', f'--platform={target_arch}')
                    
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines).encode('utf-8')
    
    async def _unzip(self, content: bytes, dest: str):
        """解压 ZIP 文件"""
        import zipfile
        import io
        
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(dest)
        
        # 检测并修复嵌套的根目录（如果归档有单层根目录则平铺）
        await self._flatten_nested_archive(dest)
    
    async def _untar(self, content: bytes, dest: str):
        """解压 TAR 文件"""
        import tarfile
        import io
        
        with tarfile.open(fileobj=io.BytesIO(content)) as tf:
            tf.extractall(dest)
        
        # 检测并修复嵌套的根目录（如果归档有单层根目录则平铺）
        await self._flatten_nested_archive(dest)
    
    async def _flatten_nested_archive(self, dest: str):
        """
        检测并修复嵌套的根目录结构。
        
        如果归档解压后只有一个目录作为根目录（常见于从某个目录打包的情况），
        则将内容平铺到 dest 目录，避免 COPY 指令找不到文件。
        """
        try:
            entries = os.listdir(dest)
            
            # 如果解压后只有一个目录，可能是嵌套结构
            if len(entries) == 1:
                nested_dir = os.path.join(dest, entries[0])
                
                if os.path.isdir(nested_dir):
                    # 检查嵌套目录是否直接包含 Dockerfile 或 src 等典型文件
                    # 而不是更多子目录（如果是完整项目目录则不移动）
                    nested_contents = os.listdir(nested_dir)
                    
                    has_dockerfile = 'Dockerfile' in nested_contents
                    has_dockerignore = any('dockerignore' in f.lower() for f in nested_contents)
                    
                    # 如果嵌套目录包含 Dockerfile 或 .dockerignore，
                    # 说明这是用户从项目根目录打包的，应该平铺
                    if has_dockerfile or has_dockerignore:
                        logger.info(f"检测到嵌套根目录 '{entries[0]}'，正在平铺到构建上下文根目录...")
                        
                        # 将嵌套目录的内容移动到 dest
                        for item in nested_contents:
                            src = os.path.join(nested_dir, item)
                            dst = os.path.join(dest, item)
                            
                            # 如果目标已存在同名文件/目录，先删除
                            if os.path.exists(dst):
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            
                            shutil.move(src, dst)
                        
                        # 删除空嵌套目录
                        if not os.listdir(nested_dir):
                            os.rmdir(nested_dir)
                            
                        logger.info(f"嵌套目录已平铺完成")
        except Exception as e:
            logger.warning(f"修复嵌套目录结构失败（非致命）: {e}")
    
    async def _cleanup(self, *paths):
        """清理临时文件"""
        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                logger.warning(f"清理失败 {path}: {e}")
    
    async def _setup_buildkit_config(self, mirrors: list) -> Optional[str]:
        """
        为 BuildKit 配置 registry mirrors
        
        BuildKit (docker buildx build) 不读取 daemon.json 的 registry-mirrors，
        需要创建 buildkitd.toml 配置文件。
        
        Args:
            mirrors: 镜像源列表，如 ["docker.1panel.live", "docker.m.daocloud.io"]
        
        Returns:
            配置文件的路径，失败返回 None
        """
        # 构建 TOML 配置（注意：mirrors 不要加 https:// 前缀）
        # TOML 格式要求：mirrors 数组必须在 section 下且不能有额外缩进
        mirrors_list = ', '.join(f'"{m}"' for m in mirrors)
        toml_content = f"""# BuildKit registry mirrors 配置
[registry."docker.io"]
mirrors = [{mirrors_list}]
"""
        
        # 按优先级尝试写入位置（用户目录优先，因为不需要 root）
        config_paths = [
            os.path.expanduser("~/.docker/buildkitd.toml"),  # 用户目录优先
            "/etc/buildkitd.toml",  # 系统目录
            "/tmp/buildkitd.toml"   # 临时目录作为最后备选
        ]
        
        for config_path in config_paths:
            try:
                config_dir = os.path.dirname(config_path)
                os.makedirs(config_dir, exist_ok=True)
                with open(config_path, 'w') as f:
                    f.write(toml_content)
                logger.info(f"BuildKit registry mirrors 已配置: {config_path}")
                return config_path
            except PermissionError:
                logger.warning(f"权限不足无法写入 {config_path}，尝试下一个位置")
                continue
            except Exception as e:
                logger.warning(f"写入 {config_path} 失败: {e}")
                continue
        
        logger.warning("无法写入 BuildKit 配置文件，registry mirrors 可能不生效")
        return None


# 全局实例
docker_builder = DockerBuilder()
