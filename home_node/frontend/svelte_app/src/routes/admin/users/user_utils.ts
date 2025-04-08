import { api_fetch_srv } from "$lib/server/utils";
import { type Row } from "$lib/table";
import type { User } from "$lib/utils/const";
import type { JWTTokenWithRawStr } from "$lib/utils/token";
import type { RequestEvent, ServerLoadEvent } from "@sveltejs/kit";

// export interface CacheContainer<T> {
//     timestamp: number;
//     data: T;
// }

const CACHE_DURATION = 60_000;
let service_name_cache_data: string[] = [];
let service_name_cache_ts = 0;

export const service_name_get_set_cache = async (event: ServerLoadEvent | RequestEvent, token: JWTTokenWithRawStr) => {
    const datenow = Date.now();
    if (datenow - service_name_cache_ts >= CACHE_DURATION) {
        const resp = await api_fetch_srv(event, token, "internal/service/names");
        if (resp.ok) {
            service_name_cache_ts = datenow;
            service_name_cache_data = await resp.json();
        }
    }
    return service_name_cache_data;
};

export const HEADERS = {
    user: "User/ID",
    namemail: "Name/Mail",
    role: "Role",
    created: "Created",
};
export type HeaderKeys = keyof typeof HEADERS;
export const MOBILE_FILTER_HEADERS: HeaderKeys[] = ["role"];

export const convert_user_list_to_rows = (users: User[]) => {
    return users.map((user) => {
        const row: { [key in HeaderKeys]: any } = {
            user: [user.login.name, user.user_id],
            namemail: [user.data.name, user.login.mail],
            role: user.roles[0],
            created: user.registration.created,
        };
        return [row, user] as Row<HeaderKeys, User>;
    });
};
