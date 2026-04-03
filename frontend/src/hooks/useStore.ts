import { create } from 'zustand';
import type { Task, Architecture, LogEntry } from '@/types';

interface BuildState {
  // Current task
  currentTask: Task | null;
  isBuilding: boolean;
  
  // Logs
  logs: LogEntry[];
  
  // Actions
  setCurrentTask: (task: Task | null) => void;
  updateTask: (updates: Partial<Task>) => void;
  setIsBuilding: (isBuilding: boolean) => void;
  addLog: (log: LogEntry) => void;
  setLogs: (logs: LogEntry[]) => void;
  clearLogs: () => void;
  reset: () => void;
}

export const useBuildStore = create<BuildState>((set) => ({
  currentTask: null,
  isBuilding: false,
  logs: [],
  
  setCurrentTask: (task) => set({ currentTask: task }),
  
  updateTask: (updates) => set((state) => ({
    currentTask: state.currentTask 
      ? { ...state.currentTask, ...updates }
      : null,
  })),
  
  setIsBuilding: (isBuilding) => set({ isBuilding }),
  
  addLog: (log) => set((state) => ({
    logs: [...state.logs.slice(-999), log],
  })),
  
  setLogs: (logs) => set({ logs }),
  
  clearLogs: () => set({ logs: [] }),
  
  reset: () => set({
    currentTask: null,
    isBuilding: false,
    logs: [],
  }),
}));

// Architecture selection store
interface SelectState {
  selectedArch: Architecture;
  setSelectedArch: (arch: Architecture) => void;
}

export const useArchStore = create<SelectState>((set) => ({
  selectedArch: 'linux/amd64',
  setSelectedArch: (arch) => set({ selectedArch: arch }),
}));
