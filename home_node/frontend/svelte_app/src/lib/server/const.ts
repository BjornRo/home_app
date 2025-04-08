import { RolesEnum } from "$lib/utils/const";
import type { JWTTokenWithRawStr } from "$lib/utils/token";

export const LOCAL_API_HOST = "http://127.0.0.1:8888/";

export const NAVBAR_ITEMS = ["admin", "settings", "home", "dashboard"];

export const IP_HEADER = "X-Real-IP";
export const SERVICE_HEADER = "X-Service";

export class InternalRolesEnum {
    static ROOT = "root" as const;
    static MQTT = "mqtt" as const;
    static REMOTE = "remote" as const;
    static GLOBAL = "global" as const;
    static LOCAL = "local" as const;
    static HOME = "home" as const;
    static CACHE = "cache" as const;
    static API = "api" as const;
}

export class AppUser {
    name: string;
    roles: RolesEnum[];

    constructor(name: string, roles: RolesEnum[]) {
        this.name = name;
        this.roles = roles;
    }

    is_root() {
        return this.roles.some((s) => s === RolesEnum.ROOT);
    }
    is_mod() {
        return this.roles.some((s) => s === RolesEnum.MOD);
    }
}

export interface RawAppUser {
    name: string;
    roles: string[];
}

export interface UserToken {
    user: AppUser;
    token: JWTTokenWithRawStr;
}
