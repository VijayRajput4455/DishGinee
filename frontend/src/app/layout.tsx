import type { Metadata } from 'next';
import Sidebar from '@/components/Sidebar';
import './globals.css';

export const metadata: Metadata = {
  title: 'DishGenie - AI-Powered Recipe Generator',
  description: 'Smart kitchen companion using YOLO computer vision, Whisper speech-to-text, and Ollama LLMs.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="layout-wrapper">
          <Sidebar />
          <div className="main-wrapper">
            <main>{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
