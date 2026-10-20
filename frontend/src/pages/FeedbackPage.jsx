import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getFeedback } from '../api/interviews';
import { getErrorMessage, formatDate } from '../utils/helpers';
import Card from '../components/Card';
import Button from '../components/Button';
import Loader from '../components/Loader';
import {
  ArrowLeft,
  MessageSquare,
  Lightbulb,
  BrainCircuit,
  User,
} from 'lucide-react';

export default function FeedbackPage() {
  const { interviewId } = useParams();
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getFeedback(interviewId);
        if (!cancelled) setFeedback(data);
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [interviewId]);

  if (loading) return <Loader message="Loading feedback..." />;

  if (error) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700" role="alert">
          {error}
        </div>
      </div>
    );
  }

  if (!feedback) return null;

  const { details, strengths, weaknesses, transcript } = feedback;

  return (
    <div className="mx-auto max-w-3xl">
      {/* Back + header */}
      <div className="mb-6">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-body hover:text-heading mb-3">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to dashboard
        </Link>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-heading">{feedback.target_role}</h1>
            <p className="text-sm text-body">Completed {formatDate(feedback.completed_at)}</p>
          </div>
        </div>
      </div>

      {/* Summary */}
      {details.summary && (
        <Card className="mb-6">
          <h2 className="mb-2 text-base font-semibold text-heading flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" aria-hidden="true" />
            Summary
          </h2>
          <p className="text-sm leading-relaxed text-body">{details.summary}</p>
        </Card>
      )}

      {/* Strengths & Weaknesses side by side */}
      <div className="grid gap-6 md:grid-cols-2 mb-6">
        {strengths.length > 0 && (
          <Card>
            <h2 className="mb-3 text-base font-semibold text-heading flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-green-600" aria-hidden="true" />
              Strengths
            </h2>
            <ul className="space-y-3">
              {strengths.map((s, i) => (
                <li key={i} className="border-l-2 border-green-400 pl-3">
                  <p className="text-sm font-medium text-heading">{s.point}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {weaknesses.length > 0 && (
          <Card>
            <h2 className="mb-3 text-base font-semibold text-heading flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-red-500" aria-hidden="true" />
              Areas to Improve
            </h2>
            <ul className="space-y-3">
              {weaknesses.map((w, i) => (
                <li key={i} className="border-l-2 border-red-400 pl-3">
                  <p className="text-sm font-medium text-heading">{w.point}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      {/* Communication feedback */}
      {details.communication_feedback && (
        <Card className="mb-6">
          <h2 className="mb-2 text-base font-semibold text-heading flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" aria-hidden="true" />
            Communication Feedback
          </h2>
          <p className="text-sm leading-relaxed text-body">{details.communication_feedback}</p>
        </Card>
      )}

      {/* Improvement areas */}
      {details.improvement_areas?.length > 0 && (
        <Card className="mb-6">
          <h2 className="mb-3 text-base font-semibold text-heading flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-yellow-500" aria-hidden="true" />
            How to Improve
          </h2>
          <div className="space-y-4">
            {details.improvement_areas.map((area, i) => (
              <div key={i} className="rounded-lg border border-border bg-gray-50 p-3">
                <p className="text-sm font-semibold text-heading">{area.area}</p>
                <p className="mt-0.5 text-xs text-body">{area.why}</p>
                <p className="mt-1 text-xs font-medium text-primary">
                  &rarr; {area.how_to_improve}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Transcript */}
      {transcript.length > 0 && (
        <Card className="mb-6">
          <h2 className="mb-4 text-base font-semibold text-heading">Interview Transcript</h2>
          <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
            {transcript.map((msg, idx) => (
              <div key={idx} className={`flex gap-2 ${msg.role === 'candidate' ? 'justify-end' : ''}`}>
                {msg.role === 'interviewer' && (
                  <div className="mt-0.5 shrink-0 rounded-full bg-green-50 p-1.5">
                    <BrainCircuit className="h-3 w-3 text-primary" aria-hidden="true" />
                  </div>
                )}
                <div
                  className={`max-w-[75%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                    msg.role === 'candidate'
                      ? 'bg-primary/10 text-heading'
                      : 'bg-gray-50 border border-border text-heading'
                  }`}
                >
                  {msg.content}
                </div>
                {msg.role === 'candidate' && (
                  <div className="mt-0.5 shrink-0 rounded-full bg-green-50 p-1.5">
                    <User className="h-3 w-3 text-primary" aria-hidden="true" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Back button */}
      <div className="flex justify-center pb-8">
        <Link to="/">
          <Button variant="secondary">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
