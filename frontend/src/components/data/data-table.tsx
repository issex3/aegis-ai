"use client";

import {
  columnFilteringFeature,
  createFilteredRowModel,
  createPaginatedRowModel,
  createSortedRowModel,
  filterFn_includesString,
  globalFilteringFeature,
  rowPaginationFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  sortFn_text,
  tableFeatures,
  useTable,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export const researchTableFeatures = tableFeatures({
  columnFilteringFeature,
  rowSortingFeature,
  rowPaginationFeature,
  globalFilteringFeature,
  sortedRowModel: createSortedRowModel(),
  filteredRowModel: createFilteredRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
  sortFns: {
    alphanumeric: sortFn_alphanumeric,
    basic: sortFn_basic,
    text: sortFn_text,
  },
  filterFns: {
    includesString: filterFn_includesString,
  },
});

type DataTableProps<TData extends RowData> = {
  columns: Array<ColumnDef<typeof researchTableFeatures, TData>>;
  data: TData[];
  className?: string;
  emptyMessage?: string;
  tableKey?: string;
  pageSize?: number;
  filterPlaceholder?: string;
};

/**
 * TanStack Table v9 shell with sorting, global filter, and pagination.
 * Pass authoritative records only — never fabricate security events.
 */
export function DataTable<TData extends RowData>({
  columns,
  data,
  className,
  emptyMessage = "No rows.",
  tableKey,
  pageSize = 8,
  filterPlaceholder = "Filter rows…",
}: DataTableProps<TData>) {
  const table = useTable({
    ...(tableKey ? { key: tableKey } : {}),
    features: researchTableFeatures,
    columns,
    data,
    initialState: {
      pagination: { pageIndex: 0, pageSize },
    },
  });

  const rows = table.getRowModel().rows;
  const pageCount = table.getPageCount();

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <input
          value={String(table.state.globalFilter ?? "")}
          onChange={(event) => table.setGlobalFilter(event.target.value)}
          placeholder={filterPlaceholder}
          className="h-10 w-full border border-input bg-[#0c0c10] px-3 text-sm text-foreground sm:max-w-xs"
        />
        <p className="font-mono text-[11px] text-faint">
          {data.length} row{data.length === 1 ? "" : "s"}
        </p>
      </div>
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort?.() ?? false;
                const sorted = header.column.getIsSorted?.();
                return (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : canSort ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 uppercase tracking-wide"
                        onClick={header.column.getToggleSortingHandler?.()}
                      >
                        <table.FlexRender header={header} />
                        <span className="font-mono text-[9px] text-faint">
                          {sorted === "asc" ? "↑" : sorted === "desc" ? "↓" : "↕"}
                        </span>
                      </button>
                    ) : (
                      <table.FlexRender header={header} />
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="py-8 text-center text-muted-foreground">
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <TableRow key={row.id}>
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id}>
                    <table.FlexRender cell={cell} />
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {pageCount > 1 ? (
        <div className="flex items-center justify-between gap-3">
          <p className="font-mono text-[11px] text-faint">
            Page {(table.state.pagination?.pageIndex ?? 0) + 1} / {pageCount}
          </p>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="outline" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}>
              Previous
            </Button>
            <Button type="button" size="sm" variant="outline" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}>
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
