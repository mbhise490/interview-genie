import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { startInterview, submitAnswer, endInterview } from '../api/interviews';
import { getErrorMessage } from '../utils/helpers';
import { useToast } from '../context/ToastContext';
import Button from '../components/Button';
import Card from '../components/Card';
import Loader from '../components/Loader';
import { Send, StopCircle, BrainCircuit, User } from 'lucide-react';

export default function InterviewPage() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const [messages, setMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState('');

  /* Scroll to bottom when messages change */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentQuestion]);

  /* Start the interview on mount */
  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const data = await startInterview(interviewId);
        if (cancelled) return;
        if (data.status === 'completed') {
          addToast('This interview is already completed.');
          navigate(`/feedback/${interviewId}`, { replace: true });
          return;
        }
        setCurrentQuestion(data.message);
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    init();
    return () => { cancelled = true; };
  }, [interviewId, navigate, addToast]);

  async function handleSubmitAnswer(evt) {
    evt.preventDefault();
    if (!answer.trim() || submitting) return;

    const userAnswer = answer.trim();
    setMessages((prev) => [
      ...prev,
      { role: 'interviewer', content: currentQuestion },
      { role: 'candidate', content: userAnswer },
    ]);
    setCurrentQuestion('');
    setAnswer('');
    setSubmitting(true);

    try {
      const data = await submitAnswer(interviewId, userAnswer);
      if (data.status === 'completed') {
        addToast('Interview completed! Redirecting to feedback...');
        navigate(`/feedback/${interviewId}`, { replace: true });
        return;
      }
      setCurrentQuestion(data.message);
    } catch (err) {
      /* Restore the question so the user can retry */
      setCurrentQuestion(currentQuestion);
      setMessages((prev) => prev.slice(0, -2));
      addToast(getErrorMessage(err), 'error');
    } finally {
      setSubmitting(false);
      inputRef.current?.focus();
    }
  }

  async function handleEndEarly() {
    if (ending) return;
    setEnding(true);
    try {
      await endInterview(interviewId);
      addToast('Interview ended. Your feedback is ready!');
      navigate(`/feedback/${interviewId}`, { replace: true });
    } catch (err) {
      addToast(getErrorMessage(err), 'error');
      setEnding(false);
    }
  }

  if (loading) return <Loader message="Starting your interview..." />;

  if (error) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700" role="alert">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header bar */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-heading">Mock Interview</h1>
        </div>
        <Button
          variant="danger"
          onClick={handleEndEarly}
          loading={ending}
          disabled={messages.length === 0 && !currentQuestion}
        >
          <StopCircle className="h-4 w-4" aria-hidden="true" />
          End Interview
        </Button>
      </div>

      {/* Message history */}
      <div className="space-y-4 mb-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'candidate' ? 'justify-end' : ''}`}>
            {msg.role === 'interviewer' && (
              <div className="mt-0.5 shrink-0 rounded-full bg-green-50 p-2">
                <BrainCircuit className="h-4 w-4 text-primary" aria-hidden="true" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'candidate'
                  ? 'bg-primary text-white'
                  : 'border border-border bg-gray-50 text-heading'
              }`}
            >
              {msg.content}
            </div>
            {msg.role === 'candidate' && (
              <div className="mt-0.5 shrink-0 rounded-full bg-green-50 p-2">
                <User className="h-4 w-4 text-primary" aria-hidden="true" />
              </div>
            )}
          </div>
        ))}

        {/* Current question */}
        {currentQuestion && (
          <div className="flex gap-3">
            <div className="mt-0.5 shrink-0 rounded-full bg-green-50 p-2">
              <BrainCircuit className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <Card className="max-w-[80%] !py-3 !px-4">
              <p className="text-sm leading-relaxed text-heading">{currentQuestion}</p>
            </Card>
          </div>
        )}

        {submitting && (
          <div className="flex gap-3">
            <div className="mt-0.5 shrink-0 rounded-full bg-green-50 p-2">
              <BrainCircuit className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <div className="rounded-xl border border-border bg-gray-50 px-4 py-3">
              <div className="flex gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '0ms' }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '150ms' }} />
                <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Answer input */}
      {currentQuestion && !submitting && (
        <form onSubmit={handleSubmitAnswer} className="sticky bottom-4">
          <div className="flex gap-2 rounded-xl border border-border bg-white p-2 shadow-lg">
            <textarea
              ref={inputRef}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer..."
              className="flex-1 resize-none rounded-lg border-0 px-3 py-2 text-sm text-heading placeholder:text-gray-400 focus:outline-none"
              rows={2}
              maxLength={4000}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmitAnswer(e);
                }
              }}
              aria-label="Your answer"
            />
            <Button type="submit" disabled={!answer.trim()} className="self-end">
              <Send className="h-4 w-4" aria-hidden="true" />
              Send
            </Button>
          </div>
          <p className="mt-1 text-center text-xs text-gray-400">
            Press Enter to send, Shift+Enter for new line
          </p>
        </form>
      )}
    </div>
  );
}
