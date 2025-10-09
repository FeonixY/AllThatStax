declare module "react" {
  export type ReactNode = any;
  export type FC<P = any> = (props: P) => any;
  export interface CSSProperties {
    [key: string]: string | number;
  }
  export type ChangeEvent<T = any> = any;
  export type DragEvent<T = any> = any;
  export type MouseEvent<T = any> = any;

  export const Fragment: any;
  export const StrictMode: any;
  export function useState<T = any>(
    initial?: T
  ): [T, (value: T | ((prev: T) => T)) => void];
  export function useEffect(effect: (...args: any[]) => any, deps?: any[]): void;
  export function useMemo<T = any>(factory: () => T, deps?: any[]): T;
  export function useCallback<T = any>(callback: T, deps?: any[]): T;
  export function useRef<T = any>(value: T): { current: T };
  export function useReducer(...args: any[]): any;
  export const createElement: any;
  export default {
    createElement: any,
    Fragment,
    StrictMode,
    useState,
    useEffect,
    useMemo,
    useCallback,
    useRef,
    useReducer,
  };
}

declare module "react-dom/client" {
  export const createRoot: any;
  export default { createRoot };
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

declare namespace React {
  type DragEvent<T = any> = any;
  type ChangeEvent<T = any> = any;
}
