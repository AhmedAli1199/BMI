"use client";

import { useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { DataView } from "@/components/data-view/data-view";
import { type Accessors, type SortAccessors, applyFilters, facetCounts, sortRows } from "@/lib/data-view/client-engine";
import { type FilterDef, type SortState, parseFilters, parseSort } from "@/lib/data-view/schema";

/** A DataView over rows already in the browser: filters, sorts and counts
 * facets locally, then hands the visible rows to `children`. Same sidebar,
 * chips and sortable headers as the database-backed tables. */
export function ClientDataView<Row>({
  rows,
  defs,
  defaultSort,
  accessors,
  sortAccessors,
  children,
}: {
  rows: Row[];
  defs: FilterDef[];
  defaultSort: SortState;
  accessors: Accessors<Row>;
  sortAccessors: SortAccessors<Row>;
  children: (visible: Row[]) => React.ReactNode;
}) {
  const search = useSearchParams();
  const values = useMemo(() => parseFilters(defs, search), [defs, search]);
  const sort = useMemo(() => parseSort(search, defaultSort), [search, defaultSort]);
  const facets = useMemo(() => facetCounts(rows, defs, values, accessors), [rows, defs, values, accessors]);
  const visible = useMemo(
    () => sortRows(applyFilters(rows, defs, values, accessors), sort, sortAccessors),
    [rows, defs, values, accessors, sort, sortAccessors]
  );
  return (
    <DataView defs={defs} defaultSort={defaultSort} facets={facets} shallow>
      {children(visible)}
    </DataView>
  );
}
