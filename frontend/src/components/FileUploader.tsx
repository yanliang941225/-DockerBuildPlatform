import { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatBytes } from '@/lib/utils';

interface FileUploaderProps {
  maxSize?: number;
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  title: string;
  description: string;
  disabled?: boolean;
  allowedExtensions?: string[];
}

// 验证文件扩展名
function validateExtension(file: File, allowedExtensions: string[]): FileRejection[] {
  if (allowedExtensions.length === 0) return [];
  
  const filename = file.name;
  const lowerFilename = filename.toLowerCase();
  
  // 检查完全匹配（如 Dockerfile）
  if (allowedExtensions.some(e => e.toLowerCase() === lowerFilename)) {
    return [];
  }
  
  // 检查扩展名
  for (const ext of allowedExtensions) {
    const cleanExt = ext.startsWith('.') ? ext.toLowerCase() : '.' + ext.toLowerCase();
    if (lowerFilename.endsWith(cleanExt)) {
      return [];
    }
  }
  
  return [{
    file,
    errors: [{
      code: 'file-invalid-type',
      message: `不支持的文件类型，仅支持: ${allowedExtensions.join(', ')}`
    }]
  }];
}

export function FileUploader({
  maxSize = 500 * 1024 * 1024,
  onFileSelect,
  selectedFile,
  title,
  description,
  disabled = false,
  allowedExtensions = [],
}: FileUploaderProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      setError(null);

      // 自定义扩展名验证
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        const extensionErrors = validateExtension(file, allowedExtensions);
        
        if (extensionErrors.length > 0) {
          setError(extensionErrors[0].errors[0]?.message || '文件验证失败');
          return;
        }
        
        onFileSelect(file);
      }
      
      // 处理浏览器拒绝的文件
      if (fileRejections.length > 0) {
        const errorMsg = fileRejections[0].errors[0]?.message || '文件验证失败';
        setError(errorMsg);
      }
    },
    [onFileSelect, allowedExtensions]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize,
    multiple: false,
    disabled,
    // 不设置 accept，让浏览器接受所有文件，由我们自定义验证
  });

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null as unknown as File);
    setError(null);
  };

  return (
    <div
      {...getRootProps()}
      className={cn(
        'relative cursor-pointer rounded-xl border-2 border-dashed transition-all duration-200',
        isDragActive
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-border hover:border-primary/50 hover:bg-muted/30',
        disabled && 'opacity-50 cursor-not-allowed',
        selectedFile ? 'border-green-500 bg-green-50/50' : '',
        error ? 'border-red-500 bg-red-50/50' : ''
      )}
    >
      <input {...getInputProps()} />

      {selectedFile ? (
        <div className="flex items-center justify-between p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 text-green-600">
              <CheckCircle className="h-6 w-6" />
            </div>
            <div>
              <p className="font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                {formatBytes(selectedFile.size)}
              </p>
            </div>
          </div>
          {!disabled && (
            <button
              onClick={handleRemove}
              className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      ) : error ? (
        <div className="p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-red-100 text-red-600">
              <AlertCircle className="h-6 w-6" />
            </div>
            <div>
              <p className="font-medium text-red-600">上传失败</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div
            className={cn(
              'mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors',
              isDragActive && 'bg-primary/20 scale-110'
            )}
          >
            {isDragActive ? (
              <File className="h-7 w-7" />
            ) : (
              <Upload className="h-7 w-7" />
            )}
          </div>
          <p className="mb-1 font-medium text-foreground">{title}</p>
          <p className="text-sm text-muted-foreground">{description}</p>
          <p className="mt-2 text-xs text-muted-foreground/70">
            最大 {formatBytes(maxSize)}
          </p>
        </div>
      )}
    </div>
  );
}
