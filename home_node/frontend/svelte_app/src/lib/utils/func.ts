import { get } from "svelte/store";
import { API_HOST, HTTP_METHOD, RWX_MAP, TOKEN_PATH, type SensorData, type UserDataTokenExpiry } from "./const";
import { credentials } from "./stores";
import { is_expired } from "./token";
import type { LayoutLoadEvent } from "../../routes/$types";
import { redirect } from "@sveltejs/kit";

// #region Identify what type/attribute
export const is_str = (value: any): value is string => typeof value === "string" || value instanceof String;
export const is_arr = (value: any): value is any[] => Array.isArray(value);
export const is_int = (value: any) =>
    (typeof value === "string" && /^\d+$/.test(value)) || (typeof value === "number" && Number.isInteger(value));
export const is_arr_empty = (value: Array<any>): boolean => !value.length;
export const is_obj = (value: any): value is { [key: string]: any } =>
    typeof value === "object" && value !== null && !Array.isArray(value);
export const is_obj_empty = (obj: Object): boolean => Object.keys(obj).length === 0;
export const is_isodate = (value: any): null | Date => {
    const date = new Date(value);
    return !isNaN(date.getTime()) && value.endsWith("Z") ? date : null;
};
// #endregion

// #region Mapping: A -> B, A -> A, A -> Optional[B]
export const str_to_int = (value: string) => (is_int(value) ? parseInt(value) : null);
export const rwx_num_to_str = (rwx_num: number) => RWX_MAP[rwx_num];
export const rwx_str_to_num = (rwx_str: string) => RWX_MAP.indexOf(rwx_str);
export const strfloat_decimals = (elem: string | number, decimals: number) => {
    let leading_zero = false;
    if (typeof elem === "string") {
        if (elem[0] === "0") {
            leading_zero = true;
        }
        elem = parseFloat(elem);
    }
    if (Number.isInteger(elem)) {
        return elem.toString();
    }
    elem = elem.toFixed(decimals);
    if (leading_zero) {
        return elem;
    }
    return elem.substring(1);
};
// #endregion

// #region Datetime related
export const datetime_utcnow = (): Date => new Date(new Date().getTime());
export const datetime_localdate = (): Date => {
    const date = new Date();
    const localdate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return localdate;
};
// #endregion

// #region String extension
export const capitalize = (str: string) => str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
// #endregion

// #region Validation
export const validate_name_length = (name: string) => 1 <= name.length;
export const validate_mail = (mail: string) => {
    if (mail.length < 6) {
        return false;
    }
    const re =
        /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(mail);
};
export const validate_password = (password: string) => {
    if (password.length >= 8 && password.length <= 60) {
        const upper = /[A-Z]/.test(password);
        const lower = /[a-z]/.test(password);
        const digit = /\d/.test(password);
        return upper && lower && digit;
    }
    return false;
};
export const validate_guid = (input: string, exact_len: boolean = false) =>
    (!exact_len || input.length === 20) && /^[a-z0-9]+$/.test(input);
// #endregion

// #region HTML funcs
export const contains = (element: HTMLElement | null, ignore_classes: string[]): boolean => {
    if (element === null) {
        return false;
    } else if (ignore_classes.some((cls) => element.classList.contains(cls))) {
        return true;
    }
    return contains(element.parentElement, ignore_classes);
};
// #endregion

export const copy = <T>(o: T) => JSON.parse(JSON.stringify(o)) as T;
export const uuid4 = () => {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c: string) => {
        const r = (Math.random() * 16) | 0;
        const v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
};

export const get_creds = () => get(credentials);
export const api_path = (path: string) => API_HOST + path;
export const gen_header = (token: string) => ({ headers: { Authorization: `Bearer ${token}` } });

export const get_sensor_data = async (sfetch: any): Promise<SensorData | null> => {
    const f = sfetch ?? fetch;
    return await f(api_path("data/sensors")).then((resp: any) => (resp.ok ? resp.json() : null));
};

// export const unsafe_decode_jwt = (token: string): JWTTokenWithRawStr => ({
//     raw_token: token,
//     ...(JSON.parse(atob(token.substring(token.indexOf(".") + 1, token.lastIndexOf(".")))) as JWTToken),
// });

interface Opts {
    method: HTTP_METHOD;
    mode: "cors" | "no-cors" | "same-origin";
    credentials: "include" | "same-origin" | "omit";
    headers: Record<string, string>;
    body?: string;
}

const cookie_base = (method: HTTP_METHOD): Opts => {
    return {
        method: method,
        mode: "cors",
        credentials: "include",
        headers: {
            "Access-Control-Allow-Origin": API_HOST,
        },
    };
};

const cookie_get_opts = () => cookie_base(HTTP_METHOD.GET);
const cookie_post_opts = (obj: Object) => {
    const cb = cookie_base(HTTP_METHOD.POST);
    cb.headers["Content-Type"] = "application/json";
    cb.body = JSON.stringify(obj);
    return cb;
};

export const api_fetch_event = async ({ fetch }: LayoutLoadEvent, path: string): Promise<Response> =>
    await fetch(api_path(path), cookie_get_opts());

export const api_fetch = async (path: string): Promise<Response> => await fetch(api_path(path), cookie_get_opts());
export const api_post = async (path: string, obj: Object): Promise<Response> =>
    await fetch(api_path(path), cookie_post_opts(obj));

//

const check_token_and_update = async (creds: UserDataTokenExpiry) => {
    if (is_expired(creds.token_expiry, 10)) {
        const res = await fetch(api_path(TOKEN_PATH), cookie_get_opts());
        if (!res.ok) {
            credentials.set(null);
            redirect(303, "/login");
        }
        credentials.set({ data: creds.data, token_expiry: parseInt(await res.text(), 10) });
    }
};
export const check_creds_then_fetch = async (path: string, method = HTTP_METHOD.GET) => {
    const creds = get(credentials);
    if (!creds) {
        return await fetch(api_path(path), { method: method });
    }
    await check_token_and_update(creds);
    return await api_fetch(path);
};

export const check_creds_then_post = async (path: string, obj: Object) => {
    const creds = get(credentials);
    if (!creds) {
        return await fetch(api_path(path), {
            method: HTTP_METHOD.POST,
            body: JSON.stringify(obj),
            headers: { "Content-Type": "application/json" },
        });
    }
    await check_token_and_update(creds);
    return await api_post(path, obj);
};
