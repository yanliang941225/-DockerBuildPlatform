"""
QEMU 跨架构支持设置模块
用于在启动时自动注册 QEMU 用户态仿真
"""
import asyncio
import logging
import subprocess
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


class QEMUSetup:
    """QEMU 设置管理器"""
    
    def __init__(self):
        self._registered = False
    
    async def register_qemu(self) -> bool:
        """
        注册 QEMU 用户态仿真
        
        Returns:
            是否成功
        """
        if self._registered:
            logger.info("QEMU 已经注册，跳过")
            return True
        
        if not settings.AUTO_REGISTER_QEMU:
            logger.info("QEMU 自动注册已禁用")
            return False
        
        logger.info("开始注册 QEMU 跨架构支持...")
        
        try:
            # 方法1：使用 multiarch/qemu-user-static 镜像
            success = await self._register_via_docker()
            
            if success:
                self._registered = True
                logger.info("QEMU 跨架构支持注册成功")
                return True
            
            # 方法2：直接注册（备选）
            success = await self._register_directly()
            
            if success:
                self._registered = True
                logger.info("QEMU 跨架构支持注册成功（直接方式）")
                return True
            
            logger.warning("QEMU 注册可能失败，请手动检查")
            return False
            
        except Exception as e:
            logger.error(f"QEMU 注册失败: {e}")
            return False
    
    async def _register_via_docker(self) -> bool:
        """通过 Docker 容器注册 QEMU"""
        try:
            cmd = [
                "docker", "run", "--rm", "--privileged",
                "multiarch/qemu-user-static:latest",
                "--reset", "-p", "yes",
                "--credential", "yes"
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )
            
            if process.returncode == 0:
                logger.info("QEMU Docker 容器注册成功")
                return True
            else:
                error = stderr.decode() if stderr else "未知错误"
                logger.warning(f"QEMU Docker 容器注册失败: {error}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("QEMU Docker 容器注册超时")
            return False
        except Exception as e:
            logger.warning(f"QEMU Docker 方式不可用: {e}")
            return False
    
    async def _register_directly(self) -> bool:
        """直接注册 QEMU（适用于已安装 qemu-user-static 的系统）"""
        arch_map = {
            "arm64": "aarch64",
            "arm/v7": "arm",
            "riscv64": "riscv64",
            "ppc64le": "ppc64le"
        }
        
        all_success = True
        
        for arch in settings.QEMU_ARCHITECTURES:
            qemu_arch = arch_map.get(arch, arch.replace("/", "-"))
            
            try:
                # 检查 qemu 二进制是否存在
                check_cmd = ["which", f"qemu-{qemu_arch}-static"]
                check_process = await asyncio.create_subprocess_exec(
                    *check_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await check_process.communicate()
                
                if check_process.returncode != 0:
                    logger.info(f"qemu-{qemu_arch}-static 未安装，跳过")
                    continue
                
                # 注册该架构
                register_cmd = [
                    "docker", "run", "--rm", "--privileged",
                    "--cap-add=ALL",
                    "-v", "/usr/bin/qemu-${ARCH}-static:/usr/bin/qemu-${ARCH}-static:ro",
                    f"multiarch/qemu-user-static:latest",
                    "--reset", "-p", "yes"
                ]
                
                cmd_str = " ".join(register_cmd).replace("${ARCH}", qemu_arch)
                logger.info(f"注册架构 {arch}...")
                
                process = await asyncio.create_subprocess_exec(
                    *register_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.info(f"架构 {arch} 注册成功")
                else:
                    logger.warning(f"架构 {arch} 注册失败")
                    all_success = False
                    
            except Exception as e:
                logger.warning(f"注册架构 {arch} 时出错: {e}")
                all_success = False
        
        return all_success
    
    async def check_buildx_available(self) -> bool:
        """检查 BuildX 是否可用"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "buildx", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                logger.info("Docker BuildX 可用")
                return True
            else:
                logger.error("Docker BuildX 不可用")
                return False
                
        except Exception as e:
            logger.error(f"检查 BuildX 时出错: {e}")
            return False
    
    async def setup_buildx_builder(self) -> bool:
        """设置 BuildX 构建器"""
        try:
            # 创建构建器
            create_cmd = [
                "docker", "buildx", "create",
                "--name", "docker-build-builder",
                "--driver", "docker-container",
                "--use"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *create_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # 如果已存在会失败，这是正常的
            
            # 启动构建器
            inspect_cmd = [
                "docker", "buildx", "inspect",
                "--bootstrap"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *inspect_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("BuildX 构建器设置成功")
                return True
            else:
                logger.warning("BuildX 构建器设置可能有问题，但继续运行")
                return True  # 不阻塞启动
                
        except Exception as e:
            logger.warning(f"设置 BuildX 构建器时出错: {e}")
            return False
    
    def is_registered(self) -> bool:
        """检查是否已注册"""
        return self._registered


# 全局实例
qemu_setup = QEMUSetup()
