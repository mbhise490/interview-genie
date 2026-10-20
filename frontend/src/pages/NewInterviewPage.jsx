import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { createInterview } from '../api/interviews';
import { getErrorMessage } from '../utils/helpers';
import { useToast } from '../context/ToastContext';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';
import { Upload, FileText, X } from 'lucide-react';

export default function NewInterviewPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const fileInputRef = useRef(null);
  const [targetRole, setTargetRole] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  function validate() {
    const e = {};
    if (!targetRole.trim()) e.targetRole = 'Target role is required.';
    else if (targetRole.trim().length < 2) e.targetRole = 'At least 2 characters.';
    if (!resumeFile) e.resume = 'Please upload your resume (PDF).';
    else if (resumeFile.type !== 'application/pdf') e.resume = 'Only PDF files are supported.';
    else if (resumeFile.size > 5 * 1024 * 1024) e.resume = 'File must be under 5 MB.';
    return e;
  }

  function handleFileChange(evt) {
    const file = evt.target.files?.[0];
    if (file) {
      setResumeFile(file);
      setErrors((prev) => ({ ...prev, resume: undefined }));
    }
  }

  function removeFile() {
    setResumeFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleSubmit(evt) {
    evt.preventDefault();
    const e = validate();
    setErrors(e);
    setServerError('');
    if (Object.keys(e).length > 0) return;

    setLoading(true);
    try {
      const result = await createInterview(targetRole.trim(), resumeFile);
      addToast('Interview created! Starting your session...');
      navigate(`/interview/${result.interview_id}`);
    } catch (err) {
      setServerError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-heading">New Mock Interview</h1>
        <p className="mt-1 text-sm text-body">
          Upload your resume and specify the role you're targeting.
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {serverError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {serverError}
            </div>
          )}

          <Input
            id="targetRole"
            label="Target Role"
            placeholder="e.g. Backend Engineer, Data Analyst"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            error={errors.targetRole}
            autoFocus
          />

          {/* File upload area */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-heading">Resume (PDF)</label>

            {!resumeFile ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={`flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-sm transition-colors hover:border-primary hover:bg-green-50 focus-ring ${
                  errors.resume ? 'border-red-400' : 'border-border'
                }`}
              >
                <Upload className="h-8 w-8 text-gray-400" aria-hidden="true" />
                <span className="text-body">Click to upload your resume</span>
                <span className="text-xs text-gray-400">PDF, max 5 MB</span>
              </button>
            ) : (
              <div className="flex items-center gap-3 rounded-lg border border-border bg-gray-50 px-4 py-3">
                <FileText className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-heading">{resumeFile.name}</p>
                  <p className="text-xs text-body">
                    {(resumeFile.size / 1024).toFixed(0)} KB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="shrink-0 rounded p-1 hover:bg-gray-200"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4 text-body" />
                </button>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="hidden"
              aria-label="Upload resume"
            />

            {errors.resume && (
              <p className="text-xs text-red-600" role="alert">{errors.resume}</p>
            )}
          </div>

          <Button type="submit" loading={loading} className="w-full">
            {loading ? 'Preparing your interview...' : 'Start Interview'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
