import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DnD RAG 战役助手',
  description: '基于 RAG 技术的 D&D DM 助手平台',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-100">{children}</body>
    </html>
  );
}
