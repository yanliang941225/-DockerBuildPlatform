// API Types

export type TaskStatus = 
  | 'pending' 
  | 'uploading' 
  | 'building' 
  | 'success' 
  | 'failed' 
  | 'cancelled' 
  | 'expired';

export type Architecture = 
  | 'linux/amd64' 
  | 'linux/arm64' 
  | 'linux/arm/v7';

export interface Task {
  task_id: string;
  status: TaskStatus;
  target_arch: string;
  created_at: string;
  expires_at: string;
  dockerfile_uploaded: boolean;
  context_uploaded: boolean;
  image_name?: string;
  image_tag?: string;
  error_message?: string;
  download_url?: string;
  download_expires_at?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

export interface BuildProgress {
  task_id: string;
  status: TaskStatus;
  progress: number;
  current_step?: string;
  logs: LogEntry[];
}

export interface UploadResponse {
  success: boolean;
  filename: string;
  size: number;
  message: string;
}

export interface ApiError {
  error: string;
  detail?: string;
  code: number;
}

// Architecture info
export const ARCHITECTURES: Record<Architecture, {
  label: string;
  description: string;
  icon: string;
  example: string;
}> = {
  'linux/amd64': {
    label: 'X86_64 (Intel/AMD)',
    description: '传统云服务器、桌面应用',
    icon: '🖥️',
    example: 'AWS EC2, 普通云服务器'
  },
  'linux/arm64': {
    label: 'ARM64 (AArch64)',
    description: 'Apple Silicon、新一代云服务器',
    icon: '🍎',
    example: 'Apple M1/M2/M3, AWS Graviton'
  },
  'linux/arm/v7': {
    label: 'ARMv7',
    description: '树莓派、嵌入式设备',
    icon: '🛠️',
    example: 'Raspberry Pi 3/4, ARM 开发板'
  },
};

// Status info
export const STATUS_INFO: Record<TaskStatus, {
  label: string;
  color: string;
  icon: string;
}> = {
  pending: {
    label: '等待中',
    color: 'text-yellow-600',
    icon: '⏳'
  },
  uploading: {
    label: '上传中',
    color: 'text-blue-600',
    icon: '📤'
  },
  building: {
    label: '构建中',
    color: 'text-blue-600',
    icon: '🔨'
  },
  success: {
    label: '构建成功',
    color: 'text-green-600',
    icon: '✅'
  },
  failed: {
    label: '构建失败',
    color: 'text-red-600',
    icon: '❌'
  },
  cancelled: {
    label: '已取消',
    color: 'text-gray-600',
    icon: '🚫'
  },
  expired: {
    label: '已过期',
    color: 'text-gray-600',
    icon: '⏰'
  },
};
