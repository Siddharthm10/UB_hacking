import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { nanoid } from 'nanoid';
import { Send, Sparkles } from 'lucide-react';
import { useCallStore } from '@/state/useCallStore';
import { getAiSocket } from '@/lib/socket';
import { streamAiAnswer } from '@/lib/api';
import { MessageBubble } from './MessageBubble';
import { TokenStream } from './TokenStream';
import { LoadingDots } from './LoadingDots';
import { cn } from '@/lib/utils';

const isDevEnv =
  typeof import.meta !== 'undefined' && import.meta.env && typeof import.meta.env.DEV !== 'undefined'
    ? import.meta.env.DEV
    : false;

const schema = z.object({
  question: z.string().min(3, 'Ask a complete question.').max(500)
});

export function AiChatBox({ isDisabled = false, className = '' }) {
  const { selectedCallId, aiChats, addAiMessage, updateAiMessage, prompts } = useCallStore();
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const abortRef = useRef(null);
  const currentStreamId = useRef(null);
  const pendingQuestion = useRef('');
  const receivedSocketToken = useRef(false);
  const socketRef = useRef(null);
  const messagesViewportRef = useRef(null);
  const previousCallIdRef = useRef(null);
  const activeCallIdRef = useRef(null);
  const streamHasContentRef = useRef(false);

  const { register, handleSubmit, reset, formState, setValue } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { question: '' }
  });

  const logAiEvent = (...args) => {
    if (isDevEnv) {
      // eslint-disable-next-line no-console
      console.debug('[AI]', ...args);
    }
  };

  useEffect(() => {
    const socket = getAiSocket();
    socketRef.current = socket;
    function handleConnect() {
      setSocketConnected(true);
    }
    function handleDisconnect() {
      setSocketConnected(false);
    }
    function handleToken(payload) {
      if (!currentStreamId.current) return;
      const targetCallId = activeCallIdRef.current;
      if (!targetCallId) return;
      receivedSocketToken.current = true;
      streamHasContentRef.current = true;
      logAiEvent('socket token', payload.token);
      updateAiMessage(targetCallId, currentStreamId.current, (msg) => ({
        content: `${msg.content || ''}${payload.token || ''}`
      }));
    }
    function handleDone() {
      const targetCallId = activeCallIdRef.current;
      finalizeStream(targetCallId);
    }
    function handleError(payload) {
      setError(payload?.message || 'AI service unavailable.');
      logAiEvent('socket error', payload);
      const targetCallId = activeCallIdRef.current || selectedCallId;
      if (pendingQuestion.current && targetCallId) {
        fallbackToHttp(pendingQuestion.current, targetCallId);
      }
    }
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('ai_token', handleToken);
    socket.on('ai_done', handleDone);
    socket.on('ai_error', handleError);
    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('ai_token', handleToken);
      socket.off('ai_done', handleDone);
      socket.off('ai_error', handleError);
    };
  }, [selectedCallId, updateAiMessage]);

  useEffect(() => () => abortRef.current && abortRef.current(), []);

  const conversation = useMemo(() => {
    if (!selectedCallId) return [];
    return aiChats[selectedCallId] ?? [];
  }, [aiChats, selectedCallId]);

  useEffect(() => {
    if (conversation.length && !isOpen) {
      setIsOpen(true);
    }
  }, [conversation.length, isOpen]);

  useEffect(() => {
    if (previousCallIdRef.current === selectedCallId) return;
    abortRef.current?.();
    abortRef.current = null;
    currentStreamId.current = null;
    pendingQuestion.current = '';
    setStatus('idle');
    setError(null);
    streamHasContentRef.current = false;
    setIsOpen(conversation.length > 0);
    activeCallIdRef.current = null;
    previousCallIdRef.current = selectedCallId;
  }, [conversation.length, selectedCallId]);

  const scrollSignature = useMemo(() => {
    return conversation
      .map((msg) => `${msg.id}-${msg.content?.length || 0}-${msg.streaming ? 1 : 0}`)
      .join('|');
  }, [conversation]);

  useEffect(() => {
    const viewport = messagesViewportRef.current;
    if (!viewport || !isOpen) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, [scrollSignature, isOpen]);

  const fallbackToHttp = (question, callId) => {
    logAiEvent('http fallback engaged', { callId });
    abortRef.current = streamAiAnswer({
      callId,
      question,
      onToken: (token) => {
        if (!currentStreamId.current) return;
        streamHasContentRef.current = true;
        logAiEvent('http token', token);
        updateAiMessage(callId, currentStreamId.current, (msg) => ({
          content: `${msg.content || ''}${token || ''}`
        }));
      },
      onDone: () => {
        finalizeStream(callId);
      },
      onError: (err) => {
        setError(err?.message || 'Unable to stream AI response.');
        finalizeStream(callId, { hadError: true });
      }
    });
  };

  const finalizeStream = (callId, { hadError = false } = {}) => {
    if (!currentStreamId.current || !callId) {
      return;
    }
    const streamId = currentStreamId.current;
    const hadContent = streamHasContentRef.current;
    const missingResponseMessage = hadError
      ? 'AI helper could not reach the language model. Please try again.'
      : 'AI helper did not return a response. Please try again.';

    updateAiMessage(callId, streamId, (msg) => {
      const hasExistingContent = Boolean((msg.content || '').trim().length);
      if (hadContent || hasExistingContent) {
        return { streaming: false };
      }
      return {
        streaming: false,
        content: missingResponseMessage
      };
    });

    if (!hadContent) {
      setError(missingResponseMessage);
    }
    logAiEvent('stream complete', { callId, hadContent, hadError });
    currentStreamId.current = null;
    activeCallIdRef.current = null;
    streamHasContentRef.current = false;
    setStatus('idle');
  };

  const onSubmit = (values) => {
    if (isDisabled || !selectedCallId) {
      setError('Select a call to start chatting with the AI helper.');
      return;
    }
    setError(null);
    const streamId = nanoid();
    pendingQuestion.current = values.question;
    addAiMessage(selectedCallId, { role: 'user', content: values.question });
    addAiMessage(selectedCallId, { id: streamId, role: 'assistant', content: '', streaming: true });
    currentStreamId.current = streamId;
    activeCallIdRef.current = selectedCallId;
    setStatus('streaming');
    streamHasContentRef.current = false;
    reset();
    if (socketRef.current?.connected) {
      receivedSocketToken.current = false;
      logAiEvent('socket emit', { callId: selectedCallId, question: values.question });
      socketRef.current.emit('ai_question', { callId: selectedCallId, question: values.question });
      setTimeout(() => {
        if (!receivedSocketToken.current) {
          logAiEvent('socket idle fallback -> http', { callId: selectedCallId });
          fallbackToHttp(values.question, selectedCallId);
        }
      }, 1200);
    } else {
      logAiEvent('socket unavailable -> http fallback', { callId: selectedCallId });
      fallbackToHttp(values.question, selectedCallId);
    }
  };

  const handlePromptClick = (prompt) => {
    if (!isOpen) {
      setIsOpen(true);
    }
    setValue('question', prompt);
  };

  const baseWrapperClass =
    'flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-slate-900/70 bg-slate-950/70 shadow-inner shadow-black/30';

  const renderStartScreen = () => (
    <div className={cn(baseWrapperClass, className)}>
      <div className="flex flex-1 items-center justify-center px-6 py-8">
        <div className="w-full max-w-lg rounded-3xl border border-slate-800/70 bg-slate-950/90 p-5 text-left text-slate-200">
          <button
            type="button"
            onClick={() => !isDisabled && setIsOpen(true)}
            disabled={isDisabled}
            className="flex w-full items-center gap-3 rounded-2xl border border-slate-800/70 bg-slate-950/80 px-4 py-3 text-left transition hover:border-primary/60 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="rounded-2xl bg-primary/20 p-2 text-primary">
              <Sparkles size={20} />
            </span>
            <span>
              <p className="text-xs font-semibold uppercase tracking-wide text-primary">AI Helper</p>
              <p className="mt-1 text-sm text-slate-400">
                Tap to start a chat about this call&apos;s transcript or risks.
              </p>
            </span>
          </button>
          <p className="mt-4 text-xs text-slate-500">
            {isDisabled ? 'Pick a call from the sidebar to enable the AI helper.' : 'Suggested prompts'}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {prompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                disabled={isDisabled}
                onClick={() => handlePromptClick(prompt)}
                className="rounded-full border border-slate-800/70 px-3 py-1 text-xs text-slate-300 transition hover:border-primary/60 hover:text-primary disabled:opacity-50"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  if (!isOpen) {
    return renderStartScreen();
  }

  const showEmptyState = conversation.length === 0;

  return (
    <div className={cn(baseWrapperClass, className)}>
      <div className="flex flex-shrink-0 items-center justify-between border-b border-slate-900/80 px-5 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Call Copilot</p>
          <p className="text-base font-semibold text-slate-100">Ask anything about this call</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-slate-800/70 px-3 py-1 text-xs text-slate-400">
          <span className={socketConnected ? 'h-2 w-2 rounded-full bg-emerald-400' : 'h-2 w-2 rounded-full bg-slate-600'} />
          {socketConnected ? 'Live stream' : 'Streaming disabled'}
        </div>
      </div>

      <div
        ref={messagesViewportRef}
        className="flex flex-1 min-h-0 flex-col space-y-4 overflow-y-auto px-5 py-6"
      >
        {showEmptyState ? (
          <div className="rounded-2xl border border-dashed border-slate-800/80 p-6 text-sm text-slate-400">
            Ask the AI to summarize the call, highlight compliance risks, or extract action items. Responses
            stream in real time with context from the selected call.
          </div>
        ) : (
          conversation.map((message) =>
            message.role === 'assistant' && message.streaming ? (
              <TokenStream key={message.id} content={message.content} streaming />
            ) : (
              <MessageBubble key={message.id} role={message.role} content={message.content} />
            )
          )
        )}
      </div>

      {error ? <p className="px-5 text-xs text-rose-300">{error}</p> : null}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="flex-shrink-0 space-y-3 border-t border-slate-900/80 px-5 py-4"
      >
        <div className="flex flex-wrap gap-2">
          {prompts.map((prompt) => (
            <button
              type="button"
              key={prompt}
              className="rounded-full border border-slate-800/80 px-3 py-1 text-xs text-slate-300 hover:border-primary/60 hover:text-primary"
              onClick={() => handlePromptClick(prompt)}
              disabled={isDisabled}
            >
              {prompt}
            </button>
          ))}
        </div>
        <div className="flex items-end gap-3 rounded-2xl border border-slate-800/70 bg-slate-900/50 px-4 py-3 focus-within:border-primary/60">
          <textarea
            rows={3}
            className="flex-1 resize-none bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500 disabled:cursor-not-allowed"
            placeholder={isDisabled ? 'Select a call to start chatting…' : 'Ask anything about the selected call…'}
            {...register('question')}
            disabled={isDisabled || status === 'streaming'}
          />
          <button
            type="submit"
            className="rounded-2xl bg-primary/80 px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-primary disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isDisabled || formState.isSubmitting || status === 'streaming'}
          >
            <div className="flex items-center gap-2">
              {status === 'streaming' ? <LoadingDots /> : <Send size={16} />}
              <span>{status === 'streaming' ? 'Streaming' : 'Send'}</span>
            </div>
          </button>
        </div>
      </form>
    </div>
  );
}
