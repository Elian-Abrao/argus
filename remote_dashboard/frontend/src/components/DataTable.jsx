function DataTable({ columns, rows, rowKey, emptyMessage = 'Sem registros para exibir.' }) {
  if (!rows || rows.length === 0) {
    return <p className="text-sm text-app-muted">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-app-border text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-app-muted ${column.headerClassName || ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-app-border/80">
          {rows.map((row, index) => (
            <tr key={rowKey ? rowKey(row, index) : index} className="transition hover:bg-app-primary/10">
              {columns.map((column) => (
                <td
                  key={`${column.key}-${rowKey ? rowKey(row, index) : index}`}
                  className={`px-3 py-2 align-top text-app-text ${column.cellClassName || ''}`}
                >
                  {column.render ? column.render(row, index) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
