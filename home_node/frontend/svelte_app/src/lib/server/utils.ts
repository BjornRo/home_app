import { createHash } from "crypto";
import type { CookieSerializeOptions } from "cookie";
import { type JWTToken, type JWTTokenWithRawStr } from "$lib/utils/token";
import { api_path } from "$lib/utils/func";
import type { RequestEvent } from "@sveltejs/kit";
import { AppUser, LOCAL_API_HOST, type UserToken } from "./const";
import type { ClaimsCacheKey } from "./token";
import { type UserDataTokenExpiry } from "$lib/utils/const";

export const api_path_server = (path: string) => LOCAL_API_HOST + path;

export const cookie_opts = (expires: number | undefined) => {
    return {
        path: "/",
        httpOnly: false,
        secure: false,
        maxAge: expires,
        // expires: typeof expires === "number" ? new Date(new Date().getTime() + expires * 1000) : undefined,
    };
};

export const hash = (m: string) => createHash("sha256").update(m).digest("hex");

export const parse_cookie = (cookie: string) => {
    const [[key, value], ...opts] = cookie.split(";").map((s) => s.trim().split("="));

    const parsed_opts = Object.fromEntries(
        opts.map(([key, _val]) => {
            let value: any = _val;
            if (value === undefined) {
                value = true;
            }
            return [key.toLowerCase(), value];
        })
    );
    if (parsed_opts.expires !== undefined) {
        parsed_opts.expires = new Date(Date.parse(parsed_opts.expires));
    }

    //     .map((v) => v.split("="))
    //     .reduce((acc: any, v) => {
    //         acc[decodeURIComponent(v[0].trim())] = decodeURIComponent(v[1].trim());
    //         return acc;
    //     }, {});

    return {
        name: key,
        value: value,
        opts: parsed_opts as CookieSerializeOptions & { path: string },
    };
};

export const api_fetch_srv = async (
    { fetch }: RequestEvent,
    token: JWTTokenWithRawStr,
    path: string
): Promise<Response> => await fetch(api_path(path), { headers: { Authorization: `Bearer ${token.raw_token}` } });

export const unsafe_jwt_to_payload_sign = (token: string): [string, string] => {
    const END = token.lastIndexOf(".");
    return [token.substring(token.indexOf(".") + 1, END), token.substring(END + 1)];
};

export const naive_decode_jwt_srv = (token: string): null | ClaimsCacheKey => {
    /* Does not verify token. header.payload.signature. Cache_key: payload.signature */
    try {
        return unsafe_decode_jwt_srv(token);
    } catch {}
    return null;
};

export const unsafe_decode_jwt_srv = (token: string): ClaimsCacheKey => {
    const [payload, sign] = unsafe_jwt_to_payload_sign(token);
    return {
        claims: {
            raw_token: token,
            ...(JSON.parse(Buffer.from(payload, "base64").toString()) as JWTToken),
        },
        cache_key: sign,
    };
};

export const jsobj_to_appuser = (js: AppUser | object): AppUser => {
    const { name, roles } = js as AppUser; // Just to get attributes
    return new AppUser(name, roles);
};

export const user_token_to_data_token = (o: UserToken): UserDataTokenExpiry => {
    return { data: { name: o.user.name }, token_expiry: o.token.exp };
};
