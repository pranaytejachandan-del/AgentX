'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { orchestrateProcurement } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Bot, Sparkles, ArrowRight, AlertCircle, CheckCircle2, Clock } from 'lucide-react';

const PRESET_PROMPTS = [
  {
    title: 'Enterprise Laptops (> ₹100k - Hackathon Judge Demo)',
    prompt: 'I need 50 enterprise laptops with 16GB RAM, delivery within 10 days, and a target price below ₹70,000 per unit.',
  },
  {
    title: 'Sustainable Office Chairs (< ₹100k - Auto Approved)',
    prompt: 'Source 500 sustainable office chairs under ₹150 each with delivery within 7 days.',
  },
  {
    title: 'High-Value Executive Desks (> ₹100k - Human Approval Required)',
    prompt: 'Source 500 premium executive desks under ₹300 each with delivery within 5 days.',
  },
];

const PROCESSING_STEPS = [
  'AgentX is parsing natural language prompt & extracting constraints...',
  'AgentX is searching catalog using pgvector semantic embeddings...',
  'AgentX is ranking candidates by Price, Lead Time, Rating, & GST...',
  'AgentX is executing multi-turn agent negotiation with supplier simulator...',
  'AgentX is evaluating 8 deterministic financial safety guardrail rules...',
];

export default function NewProcurementPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsProcessing(true);
    setErrorMsg(null);
    setCurrentStepIndex(0);

    // Activity indicator interval
    const stepInterval = setInterval(() => {
      setCurrentStepIndex((prev) => (prev < PROCESSING_STEPS.length - 1 ? prev + 1 : prev));
    }, 1200);

    try {
      const result = await orchestrateProcurement(prompt.trim());
      clearInterval(stepInterval);

      if (result.request?.id) {
        router.push(`/procurement/${result.request.id}`);
      } else {
        throw new Error('Could not obtain request ID from backend.');
      }
    } catch (err: any) {
      clearInterval(stepInterval);
      setErrorMsg(err.message || 'Procurement orchestration failed.');
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Page Title */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-sky-600 text-white flex items-center justify-center shadow-md">
          <Bot className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Create Procurement Request
          </h1>
          <p className="text-xs text-slate-500">
            State your purchasing requirements in natural language. AgentX handles discovery, negotiation, and policy safety autonomously.
          </p>
        </div>
      </div>

      <Card className="border-sky-200/80 shadow-md">
        <CardHeader className="bg-gradient-to-r from-sky-50/50 via-blue-50/30 to-white">
          <CardTitle className="text-slate-900">
            <Sparkles className="w-5 h-5 text-sky-600" />
            Natural Language Requirement Prompt
          </CardTitle>
          <span className="text-xs text-slate-400 font-medium">NLP Intent Parser — Feature 2</span>
        </CardHeader>

        <CardContent className="space-y-6 pt-6">
          {errorMsg && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              <div>
                <p className="font-bold text-rose-900">Procurement Submission Failed</p>
                <p className="mt-0.5">{errorMsg}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Describe What You Need
              </label>
              <textarea
                rows={4}
                disabled={isProcessing}
                placeholder="e.g. Source 500 sustainable office chairs under ₹150 each with delivery within 7 days..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full p-4 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm text-slate-900 font-medium placeholder-slate-400 bg-white shadow-xs resize-none disabled:bg-slate-100 disabled:cursor-not-allowed"
              />
            </div>

            {/* Agent Activity Progress Indicator */}
            {isProcessing && (
              <div className="p-4 bg-sky-50/80 border border-sky-200 rounded-xl space-y-3 animate-in fade-in duration-150">
                <div className="flex items-center gap-3 text-sky-900 font-bold text-xs">
                  <Clock className="w-4 h-4 text-sky-600 animate-spin" />
                  <span>{PROCESSING_STEPS[currentStepIndex]}</span>
                </div>

                <div className="w-full bg-sky-200 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-sky-600 h-full transition-all duration-500"
                    style={{ width: `${((currentStepIndex + 1) / PROCESSING_STEPS.length) * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isProcessing}
                disabled={!prompt.trim()}
                icon={<Sparkles className="w-4 h-4" />}
                className="w-full sm:w-auto bg-sky-600 hover:bg-sky-700 text-white font-bold"
              >
                Start AgentX
              </Button>
            </div>
          </form>

          {/* Preset Sample Prompts */}
          <div className="pt-6 border-t border-slate-100 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Quick Preset Prompts (Hackathon Demonstration)
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {PRESET_PROMPTS.map((preset, idx) => (
                <button
                  key={idx}
                  disabled={isProcessing}
                  onClick={() => setPrompt(preset.prompt)}
                  className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-sky-50/60 hover:border-sky-300 text-left transition-all group disabled:opacity-50"
                >
                  <p className="text-xs font-bold text-slate-800 group-hover:text-sky-900 mb-1">
                    {preset.title}
                  </p>
                  <p className="text-[11px] text-slate-500 line-clamp-2 italic">
                    "{preset.prompt}"
                  </p>
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
