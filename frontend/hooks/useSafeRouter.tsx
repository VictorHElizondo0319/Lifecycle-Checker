export function isStaticExport() {
    
    if (typeof window === "undefined") return false
    return window.location.protocol === 'file:';
}
export function useSafeRouter(path: string) {
    const isStatic = isStaticExport();
    console.log(path);
    if (isStatic) {
        // file:// → critical.html
        return path === "" ? "index.html" : `${path}.html`
      }
    return `/${path === "" ? "/critical" : path}`
}