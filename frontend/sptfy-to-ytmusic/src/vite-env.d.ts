/// <reference types="vite/client" />
/// <reference types="vite/types/importMeta.d.ts" />
interface ImportMetaEnv {
    readonly VITE_USER_POOL_ID: string;
    readonly VITE_USER_POOL_CLIENT_ID: string;
    readonly VITE_IDENTITY_POOL_ID: string;
    readonly VITE_AUTH_ROLE_ARN: string;
    readonly VITE_UNAUTH_ROLE_ARN: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}