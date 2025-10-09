interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly [key: string]: string | undefined;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "vite/client" {
  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string;
    readonly [key: string]: string | undefined;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}
