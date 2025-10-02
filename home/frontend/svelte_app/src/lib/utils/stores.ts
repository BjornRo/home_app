import { writable } from "svelte/store";
import type { UserDataTokenExpiry } from "./const";

export const credentials = writable<UserDataTokenExpiry | null>(null);
export const is_mobile_view = writable<boolean>(false);
