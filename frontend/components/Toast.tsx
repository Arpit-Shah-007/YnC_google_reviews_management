'use client';

import { useEffect, useState } from 'react';

interface Props {
  message: string | null;
  onDone: () => void;
}

export default function Toast({ message, onDone }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!message) return;
    setVisible(true);
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onDone, 250);
    }, 3000);
    return () => clearTimeout(t);
  }, [message, onDone]);

  if (!message) return null;

  return (
    <div
      className="toast"
      style={{ opacity: visible ? 1 : 0, transform: `translateX(-50%) translateY(${visible ? 0 : 6}px)` }}
    >
      {message}
    </div>
  );
}
