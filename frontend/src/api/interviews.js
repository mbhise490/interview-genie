import client from './client';

export async function listInterviews() {
  const response = await client.get('/interviews');
  return response.data;
}

export async function createInterview(targetRole, resumeFile) {
  const formData = new FormData();
  formData.append('target_role', targetRole);
  formData.append('resume', resumeFile);
  const response = await client.post('/interviews', formData);
  return response.data;
}

export async function startInterview(interviewId) {
  const response = await client.post(`/interviews/${interviewId}/start`);
  return response.data;
}

export async function submitAnswer(interviewId, answer) {
  const response = await client.post(`/interviews/${interviewId}/answer`, {
    answer,
  });
  return response.data;
}

export async function endInterview(interviewId) {
  const response = await client.post(`/interviews/${interviewId}/end`);
  return response.data;
}

export async function getFeedback(interviewId) {
  const response = await client.get(`/interviews/${interviewId}/feedback`);
  return response.data;
}
