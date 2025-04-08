export type Row<T extends string, R> = [Record<T, any>, R];
export type Pages<T extends string, R> = { [keys: number]: Row<T, R>[] };
export interface Column<T extends string> {
    display_name: string;
    column_key: T;
}
export class TableState<T extends string, R> {
    private all_columns: Column<T>[];
    private rows_per_page: number;
    private fetch_offset: (offset: number) => Promise<Row<T, R>[]>;
    readonly on_row_click: (callback_value: R) => void;
    readonly display_text: string;
    public max_pages: number;
    public page_number: number = 0;
    public pages: Pages<T, R> = {};
    public columns: Column<T>[];
    public number_of_rows: number;
    public is_fetching_data = false;

    constructor(
        rows_per_page: number,
        all_columns: Record<T, string>,
        display_text: string,
        number_of_rows: number = 0,
        on_row_click = (_: R) => {},
        fetch_offset: (offset: number) => Promise<Row<T, R>[]> = async () => []
    ) {
        this.rows_per_page = rows_per_page;
        this.all_columns = (Object.entries(all_columns) as [T, string][]).map(([column_key, display_name]) => ({
            display_name: display_name,
            column_key: column_key,
        }));
        this.columns = this.all_columns;
        this.display_text = display_text;
        this.number_of_rows = number_of_rows;
        this.max_pages = Math.ceil(number_of_rows / rows_per_page);
        this.on_row_click = on_row_click;
        this.fetch_offset = fetch_offset;
    }
    public init = (new_page: Row<T, R>[]) => {
        if (Object.values(this.pages).length) {
            throw "Already inited";
        }
        this.add_page(1, new_page);
        this.page_number = 1;
    };
    public page_num_ranges_validate = (page_number: number) => 0 < page_number && page_number <= this.max_pages;
    public page_num_add_validate = (page_number: number) =>
        this.page_num_ranges_validate(page_number) && !this.pages.hasOwnProperty(page_number);
    public add_page(page_number: number, new_page: Row<T, R>[]) {
        if (new_page.length > this.rows_per_page) {
            throw "Page to be inserted was larger than max rows per page";
        } else if (!this.page_num_add_validate(page_number)) {
            throw "Page number is not valid or already exists";
        }
        this.pages[page_number] = new_page;
    }
    public replace_pages(new_page: Row<T, R>[]) {
        const number_of_rows = new_page.length;
        this.number_of_rows = number_of_rows;
        if (!number_of_rows) {
            this.pages = {};
            this.max_pages = 0;
        } else {
            let page = 1;
            const rpp = this.rows_per_page;
            const result: Pages<T, R> = {};
            for (let i = 0; i < number_of_rows; i += rpp) {
                result[page] = new_page.slice(i, i + rpp);
                page += 1;
            }
            this.pages = result;
            this.page_number = 1;
            this.max_pages = Math.ceil(number_of_rows / rpp);
        }
    }
    public async fetch_page(page_number: number) {
        if (!this.page_num_add_validate(page_number)) {
            throw "Page number is not valid or already exists";
        }
        const offset = (page_number - 1) * this.rows_per_page;
        const new_page = await this.fetch_offset(offset);
        if (!new_page.length) {
            throw "No page was supplied or fetch has not been initialized";
        }
        this.pages[page_number] = new_page;
    }
    public update_columns(filter_columns: T[]): void {
        if (!filter_columns.length) {
            this.columns = this.all_columns;
        } else {
            const columns = [];
            for (const column of this.all_columns) {
                if (!filter_columns.includes(column.column_key)) {
                    columns.push(column);
                }
            }
            this.columns = columns;
        }
    }
}
