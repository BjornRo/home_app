<script lang="ts" context="module">
    import { uuid4 } from "$lib/utils/func";
    import { writable } from "svelte/store";
    import Toast from "$lib/toast.svelte";
    const toast_notify = writable<Notification[]>([]);

    export enum ToastType {
        INFO = "info",
        SUCCESS = "success",
        ERROR = "error",
    }

    export type Notification = {
        id: string;
        text: string;
        type: ToastType;
        duration: number;
        dismissible: boolean;
    };

    export const toast = {
        emit: (
            text: string,
            type: ToastType = ToastType.INFO,
            duration: number = 5000,
            dismissible: boolean = true
        ) => {
            const id = uuid4();
            toast_notify.update((all: Notification[]) => [{ id, type, duration, dismissible, text }, ...all]);
            if (duration) {
                setTimeout(() => toast.dismiss(id), duration);
            }
        },
        dismiss: (id: string) => {
            toast_notify.update((all: Notification[]) => all.filter((t) => t.id !== id));
        },
    };
</script>

{#if $toast_notify}
    <section>
        {#each $toast_notify as _toast (_toast.id)}
            <Toast data={_toast} />
        {/each}
    </section>
{/if}

<style>
    section {
        position: fixed;
        box-sizing: border-box;
        width: 100%;
        height: 100%;
        gap: 8px;
        display: flex;
        padding: 2rem;
        align-items: flex-end;
        flex-direction: column-reverse;
        z-index: 1000;
        pointer-events: none;
    }
</style>
