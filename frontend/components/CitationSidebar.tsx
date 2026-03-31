'use client';

import type { Citation } from '@/types';

interface CitationSidebarProps {
  citations: Citation[];
}

export default function CitationSidebar({ citations }: CitationSidebarProps) {
  if (!citations || citations.length === 0) {
    return (
      <div className="p-4 bg-white border rounded-lg">
        <h3 className="font-semibold mb-2">引用来源</h3>
        <p className="text-sm text-gray-500">暂无引用</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-white border rounded-lg">
      <h3 className="font-semibold mb-3">引用来源 ({citations.length})</h3>
      <ul className="space-y-3">
        {citations.map((citation, idx) => (
          <li key={idx} className="citation-card">
            <div className="flex justify-between items-start">
              <h4 className="font-medium text-sm">{citation.title}</h4>
              {citation.score && (
                <span className="text-xs text-gray-500">
                  {(citation.score * 100).toFixed(0)}%
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 mt-1 line-clamp-3">
              {citation.snippet}
            </p>
            {citation.uri && (
              <a
                href={citation.uri}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline mt-1 inline-block"
              >
                查看原文
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
