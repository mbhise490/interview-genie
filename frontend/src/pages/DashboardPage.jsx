import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listInterviews } from '../api/interviews';
import { getErrorMessage, formatDate } from '../utils/helpers';
import Card from '../components/Card';
import Button from '../components/Button';
import Loader from '../components/Loader';
import EmptyState from '../components/EmptyState';
import { PlusCircle, ClipboardList, ArrowRight } from 'lucide-react';

function StatusBadge({ status }) {
  const isComplete = status === 'completed';
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        isComplete ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
      }`}
    >
      {isComplete ? 'Completed' : 'In Progress'}
    </span>
  );
}

export default function DashboardPage() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listInterviews();
        if (!cancelled) setInterviews(data);
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <Loader message="Loading your interviews..." />;

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700" role="alert">
        {error}
      </div>
    );
  }

  if (interviews.length === 0) {
    return (
      <EmptyState
        icon={ClipboardList}
        title="No interviews yet"
        description="Start your first mock interview to get personalized feedback and improve your skills."
        action={
          <Link to="/new-interview">
            <Button>
              <PlusCircle className="h-4 w-4" aria-hidden="true" />
              Start an interview
            </Button>
          </Link>
        }
      />
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-heading">Your Interviews</h1>
          <p className="mt-1 text-sm text-body">
            {interviews.length} interview{interviews.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <Link to="/new-interview">
          <Button>
            <PlusCircle className="h-4 w-4" aria-hidden="true" />
            New Interview
          </Button>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {interviews.map((interview) => (
          <Card key={interview.interview_id} className="flex flex-col justify-between">
            <div>
              <div className="mb-3 flex items-center justify-between gap-2">
                <StatusBadge status={interview.status} />
              </div>
              <h3 className="text-base font-semibold text-heading leading-snug">
                {interview.target_role}
              </h3>
              <p className="mt-1 text-xs text-body">
                Started {formatDate(interview.created_at)}
              </p>
              {interview.completed_at && (
                <p className="text-xs text-body">
                  Completed {formatDate(interview.completed_at)}
                </p>
              )}
            </div>
            <div className="mt-4">
              {interview.status === 'completed' ? (
                <Link to={`/feedback/${interview.interview_id}`}>
                  <Button variant="secondary" className="w-full text-sm">
                    View Feedback
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </Link>
              ) : (
                <Link to={`/interview/${interview.interview_id}`}>
                  <Button variant="secondary" className="w-full text-sm">
                    Continue Interview
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </Link>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
