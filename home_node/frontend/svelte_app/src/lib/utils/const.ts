export const HOSTNAME = "bjorn.lan"; // TODO change to real api: https://api."..."
export const API_HOST = `http://${HOSTNAME}:8888/`; // TODO change to real api: https://api."..."

export const TOKEN_PATH = "auth/token";

export const MOBILE_WIDTH = 780;

export const RWX_MAP = ["---", "--x", "-w-", "-wx", "r--", "r-x", "rw-", "rwx"];

/**
 * When a new visitor enters, it is flagged as NEW if no cookie is present.
 *   Then sent to client with flag
 * The frontend then sees that this is a NEW visitor, and asks for a new session token
 *   Then if a session token is granted, refresh the website, else set cookie to null (VISITOR state)
 * When a visitor then enters, server sees the token is invalid, flags it as a visitor.
 * Else logged in
 */
export enum ACCESS_COOKIE_STATE {
    NEW = 0,
    VISITOR = 1,
    LOGGED_IN = 2,
}
export type RolesEnumValues = (typeof RolesEnum)[keyof typeof RolesEnum];

export class RolesEnum {
    static ROOT = "root" as const;
    static MOD = "mod" as const; // Moderator
    static USER = "user" as const;
}

interface Login {
    name: string;
    mail: null | string;
}

interface Registration {
    name: string;
    mail: null | string;
    created_by: string;
    created: string;
}

export interface Acl {
    resource: string;
    rwx: number;
}

export interface User {
    modified_date: string;
    user_id: string;
    login: Login;
    registration: Registration;
    roles: RolesEnum[];
    acl: Acl[];
    data: UserData;
}

export interface UserDataTokenExpiry {
    data: UserData;
    token_expiry: number;
}

export interface UserData {
    name: string;
}

export interface LocationData {
    [k: string]: Device;
}

export interface Device {
    data: DeviceData;
    date: string;
}

export interface DeviceData {
    temperature: number;
    humidity: number | undefined;
    airpressure: number | undefined;
}

export interface SensorData {
    home: LocationData;
    remote_sh: {};
}

export interface KeyValueItem {
    key: string;
    value: string;
}

export enum TimeSpec {
    MILLIS3 = "millis3", // decimals
    SECONDS = "seconds",
    MINUTES = "minutes",
}

export const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];
export const day = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export enum HTTP_METHOD {
    GET = "GET",
    PATCH = "PATCH",
    DELETE = "DELETE",
    POST = "POST",
    PUT = "PUT",
}

export type UserID = string;

export interface LiteStarException {
    status_code: number;
    detail: string;
    extra?: Record<string, any>;
}
