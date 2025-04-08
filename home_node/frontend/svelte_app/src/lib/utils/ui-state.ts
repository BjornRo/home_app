type VerifyFunc = (input: string) => boolean;
type PrintFunc = (v: string | null | undefined) => string;

export enum StateCSS {
    DEFAULT = "",
    INVALID = "error",
    VALID = "ok",
}

export class InfoPopup<T> {
    public consent_given: boolean; // Controlled by svelte component
    public enabled: boolean;
    public value: T | null;

    constructor(consent: boolean = false, value: T | null = null, enabled: boolean = true) {
        this.consent_given = consent;
        this.value = value;
        this.enabled = enabled;
    }
    public on = () => this.set_enabled(true);
    public off = () => this.set_enabled(false);
    public set_value(value: T | null) {
        if (this.value === value) {
            if (this.value !== null) {
                this.value = null; //turn off
            }
        } else {
            this.value = value;
        }
        return this.withdraw_consent();
    }
    private set_enabled(value: boolean) {
        this.enabled = value;
        return this.withdraw_consent();
    }
    private withdraw_consent = () => {
        this.consent_given = false;
        return this;
    };
}

export class TextInput {
    public state: StateCSS;
    public value: string;
    private default_value: string;
    private id: string;
    private printer: PrintFunc;
    private verifier: VerifyFunc;

    constructor(
        value: string | null,
        verify_func: VerifyFunc,
        id: string = "",
        print_func: PrintFunc = (x) => x || "",
        state: StateCSS = StateCSS.DEFAULT
    ) {
        this.printer = print_func;
        this.verifier = verify_func;
        this.id = id;
        this.state = state;
        this.default_value = this.printer(value);
        this.value = this.printer(value);
    }
    public set_state = (new_state: StateCSS) => {
        this.state = new_state;
        return this;
    };
    public get_state = (): StateCSS => this.state;
    public get_id = (): string => this.id;
    public is_valid = (): boolean => this.state !== StateCSS.INVALID;
    public get_value = (): string | null => (this.state === StateCSS.VALID ? this.value : null);
    public update_state = (value_force_lowercase: boolean) => {
        if (value_force_lowercase) {
            this.value = this.value.toLowerCase();
        }
        if (this.value === this.default_value) {
            this.state = StateCSS.DEFAULT;
        } else if (this.value !== this.default_value && this.verifier(this.value)) {
            this.state = StateCSS.VALID;
        } else {
            this.state = StateCSS.INVALID;
        }
        return this;
    };
    public reset = (new_default_value?: string | null) => {
        if (new_default_value === undefined) {
            new_default_value = this.default_value;
        } else if (new_default_value === "null") {
            new_default_value = null;
        }
        this.default_value = this.printer(new_default_value);
        this.value = this.printer(new_default_value);
        this.state = StateCSS.DEFAULT;
        return this;
    };
}

export class Checkbox {
    public value: boolean;
    private default_value: boolean;
    private id: string;

    constructor(value: boolean = false, id: string = "") {
        this.id = id;
        this.default_value = value;
        this.value = this.default_value;
    }

    public get_id = (): string => this.id;
    public is_default = (): boolean => this.value === this.default_value;
    public reset = (new_default_value?: boolean) => {
        if (new_default_value !== undefined) {
            this.default_value = new_default_value;
        }
        this.value = this.default_value;
        return this;
    };
}
