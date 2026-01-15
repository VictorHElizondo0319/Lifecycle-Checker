'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isStaticExport } from '@/hooks/useSafeRouter';

export default function Home() {
  const router = useRouter();
  
  useEffect(() => {
    const isStatic = isStaticExport();
    
    if (isStatic) {
      window.location.href = './critical.html';
    } else {
      router.push('/critical');
    }
  }, []);
}