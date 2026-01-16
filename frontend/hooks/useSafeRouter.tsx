import { useState, useEffect } from 'react';

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

/**
 * Get the current pathname that works in both web and Electron (static export) mode
 */
export function useSafePathname(): string {
    const [pathname, setPathname] = useState<string>('/');
    
    useEffect(() => {
        const updatePathname = () => {
            if (typeof window === 'undefined') return;
            
            const isStatic = isStaticExport();
            
            if (isStatic) {
                // In Electron/static export mode, use window.location
                // window.location.pathname might be like "/C:/path/to/critical.html" or just "/critical.html"
                // window.location.href might be like "file:///C:/path/to/critical.html"
                let currentPath = window.location.pathname || '';
                
                // If pathname is empty or just "/", try to get from href
                if (!currentPath || currentPath === '/') {
                    const href = window.location.href || '';
                    // Extract path from file:// URL
                    const match = href.match(/file:\/\/\/[^\/]+(.*)/);
                    if (match) {
                        currentPath = match[1];
                    }
                }
                
                // Extract filename from path (e.g., "/path/to/critical.html" -> "critical.html")
                const filename = currentPath.split('/').filter(Boolean).pop() || '';
                
                // Remove .html extension and convert to path format
                if (filename === 'index.html' || filename === '' || filename === 'index') {
                    setPathname('/critical'); // Default to critical page
                } else if (filename.endsWith('.html')) {
                    const pageName = filename.replace('.html', '');
                    setPathname(`/${pageName}`);
                } else {
                    setPathname(`/${filename}`);
                }
            } else {
                // In web mode, use window.location.pathname
                setPathname(window.location.pathname || '/');
            }
        };
        
        updatePathname();
        
        // Listen for hash changes (for Electron navigation)
        const handleHashChange = () => updatePathname();
        const handlePopState = () => updatePathname();
        
        window.addEventListener('hashchange', handleHashChange);
        window.addEventListener('popstate', handlePopState);
        
        // Check periodically in case navigation happens without events (for Electron)
        const interval = setInterval(updatePathname, 500);
        
        return () => {
            window.removeEventListener('hashchange', handleHashChange);
            window.removeEventListener('popstate', handlePopState);
            clearInterval(interval);
        };
    }, []);
    
    return pathname;
}