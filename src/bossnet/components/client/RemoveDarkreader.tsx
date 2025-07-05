'use client';

import { useEffect } from 'react';

/**
 * Client component that removes Dark Reader styles
 * This should be used in a client component to avoid SSR issues
 */
export function RemoveDarkreader() {
  useEffect(() => {
    const darkReaderStyles = Array.from(
      document.querySelectorAll<HTMLStyleElement>('style.darkreader')
    );

    if (darkReaderStyles.length) {
      darkReaderStyles.forEach((el) => el.parentElement?.removeChild(el));
    }
  }, []);

  return null;
}
