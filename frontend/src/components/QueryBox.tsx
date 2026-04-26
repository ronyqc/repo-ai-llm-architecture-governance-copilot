type QueryBoxProps = {
  query: string;
  setQuery: (value: string) => void;
};

export function QueryBox({ query, setQuery }: QueryBoxProps) {
  return (
    <textarea
      placeholder="Describe aqui el escenario de negocio..."
      value={query}
      onChange={(e) => setQuery(e.target.value)}
    />
  );
}
